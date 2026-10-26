# FinGuard AI — AWS Integration, Architecture & Deployment Guide

> **Important Notice:** This document is an architectural blueprint and deployment guide. **No paid AWS resources are created automatically.** You must review and execute these steps in your AWS account when you are ready.

---

## 1. Cloud Architecture Overview

```mermaid
flowchart TD
    Client([User Browser])
    CloudFront[Amazon CloudFront CDN (HTTPS:443)]
    S3_Frontend[(Amazon S3 - Static React Bundle)]
    Cognito[Amazon Cognito User Pool]
    AppRunner[AWS App Runner / ECS Fargate - FastAPI]
    DynamoDB[(Amazon DynamoDB - Minimal Metadata)]
    S3_Reports[(Amazon S3 - Private Reports)]

    Client -->|HTTPS :443| CloudFront
    CloudFront -->|Origin Access Control (OAC)| S3_Frontend
    Client -->|Sign-In / JWT Tokens| Cognito
    Client -->|API Requests with Bearer JWT| AppRunner
    AppRunner -->|Token RS256 JWKS Validation| Cognito
    AppRunner -->|Usage Counts & Profile Metadata| DynamoDB
    AppRunner -->|Presigned URL for Saved Exports| S3_Reports
```

### Component Breakdown
1. **Frontend Hosting**:
   - **Service**: Amazon S3 (configured with Block Public Access) + Amazon CloudFront CDN.
   - **Origin Access**: CloudFront Origin Access Control (OAC) prevents direct S3 bucket exposure.
   - **Domain / SSL**: Managed TLS certificate via AWS Certificate Manager (ACM) terminating HTTPS on port 443.
   - **SPA Routing**: CloudFront custom error response rewrites HTTP 403/404 to `/index.html` with HTTP 200.
2. **Backend API & ML Inference**:
   - **Service**: AWS App Runner (recommended for cost-efficiency, automatic HTTPS, and zero server management) or AWS ECS Fargate.
   - **Container**: `python:3.11-slim` multi-stage container running Uvicorn with 2 worker processes.
   - **Health Check Path**: `/api/health` (HTTP 200 `{"status": "healthy"}`).
3. **Authentication & Identity**:
   - **Service**: Amazon Cognito User Pool.
   - **User Groups**: `user` (default) and `admin` (elevated).
   - **Backend Token Validation**: Public keys downloaded via Cognito JWKS endpoint (`/.well-known/jwks.json`), validating RS256 signature, issuer, and client ID audience.
4. **Data Persistence**:
   - **Local Mode**: Embedded SQLite database (`data/finguard.db`) storing user metadata, bcrypt password hashes, and anonymized aggregate usage events.
   - **AWS Mode**: Amazon DynamoDB (`finguard_users`, `finguard_usage_events`, `finguard_audit_logs`) storing user profiles and privacy-preserving usage counters.
5. **Report Storage (Optional)**:
   - **Service**: Amazon S3 private bucket for explicitly saved batch reports.
   - **Security**: Block All Public Access, SSE-AES256 encryption, access via time-limited presigned URLs (1 hour expiry).
   - **Privacy Policy**: Raw transaction feature inputs and uploaded CSV files are processed in memory and **never permanently retained**.

---

## 2. Empirical Benchmark Findings & Resource Sizing Analysis

Empirical benchmarking was executed on the model artifacts using [`backend/scripts/benchmark_runtime.py`](file:///c:/Users/HP/Desktop/Project/DL%20mini%20project/FinGuard-AI/backend/scripts/benchmark_runtime.py):

### Benchmark Results Table
| Model ID | Family | Dataset | Total Size | Load Time | Single Latency (p50) | Single Latency (p95) | 1,000-Row Batch |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `credit_1_xgboost` | XGBoost | Credit Card | 524.7 KB | 2,241.5 ms | **1.60 ms** | 2.44 ms | 39.2 ms |
| `credit_1_mlp` | MLP | Credit Card | 70.1 KB | 277.5 ms | 150.37 ms | 191.69 ms | 399.5 ms |
| `credit_1_autoencoder` | Autoencoder | Credit Card | 68.1 KB | 189.3 ms | 141.39 ms | 176.47 ms | 413.8 ms |
| `paysim_2_xgboost` | XGBoost | PaySim | 56.8 KB | 3.2 ms | **1.31 ms** | 1.59 ms | 34.8 ms |
| `paysim_2_mlp` | MLP | PaySim | 70.0 KB | 168.7 ms | 136.06 ms | 188.43 ms | 327.2 ms |
| `paysim_2_autoencoder` | Autoencoder | PaySim | 40.6 KB | 147.0 ms | 138.96 ms | 175.44 ms | 311.8 ms |
| **Combined / Averages** | — | — | **0.81 MB** | **481.2 ms** | **94.95 ms** | **122.77 ms** | **254.37 ms** |

- **Peak Memory Consumption**: 8.13 MB for model weights in process heap.
- **Combined Disk Footprint**: Under 1.0 MB for all 6 verified serving models combined.
- **Inference Speed**: XGBoost executes single inference in **1.3–1.6 ms**; Neural Networks execute in **~140 ms** on CPU.
- **Batch Processing**: 1,000-row batch runs complete in **34–413 ms**.

### Hosting Service Comparison & Decision Matrix
| Hosting Option | Startup Time | Memory Required | Cost Estimate | Recommendation |
| :--- | :---: | :---: | :---: | :--- |
| **AWS App Runner** | ~3.5s | 1 vCPU, 2 GB RAM | ~$5–$15 / mo (scales to 0) | **Recommended** — Fully managed container service with built-in HTTPS, custom domains, and automatic health checking. |
| **AWS ECS Fargate** | ~15–20s | 1 vCPU, 2 GB RAM | ~$12–$25 / mo | Excellent for enterprise VPC requirements, but requires Application Load Balancer (ALB) which adds ~$16/mo baseline cost. |
| **AWS Lambda** | ~4–6s cold | 2048 MB | ~$0.00 (Free Tier) | Requires container image due to TensorFlow/Keras runtime size; cold starts cause latency spikes. |

---

## 3. Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Required | Default (Dev) | Production (AWS) Example | Description |
| :--- | :---: | :--- | :--- | :--- |
| `APP_NAME` | No | `FinGuard AI API` | `FinGuard AI API` | Service name in health endpoint. |
| `APP_ENV` | Yes | `development` | `production` | Environment flag (`development` or `production`). |
| `HOST` | Yes | `127.0.0.1` | `0.0.0.0` | Bind IP for Uvicorn server. |
| `PORT` | Yes | `8000` | `8000` | Port for incoming API requests. |
| `CORS_ORIGINS` | Yes | `http://localhost:5173` | `https://finguard.yourdomain.com` | Comma-separated allowed frontend origins. |
| `MODELS_BASE_DIR`| Yes | `../../model files/models` | `models` or `/app/models` | Relative or absolute path to model artifacts. |
| `MAX_UPLOAD_SIZE_MB`| No | `10` | `10` | Maximum batch CSV file upload size in megabytes. |
| `AUTH_PROVIDER` | Yes | `local` | `cognito` | Identity provider mode (`local` or `cognito`). |
| `JWT_SECRET_KEY` | If local | *Dev Key* | *High-entropy 256-bit secret* | Local JWT signing secret (change in production). |
| `AWS_REGION` | If AWS | `us-east-1` | `us-east-1` | Target AWS region for cloud resources. |
| `COGNITO_USER_POOL_ID` | If Cognito | `""` | `us-east-1_xxxxxxxxx` | Amazon Cognito User Pool identifier. |
| `COGNITO_APP_CLIENT_ID`| If Cognito | `""` | `xxxxxxxxxxxxxxxxxxxxxxxxxx` | Amazon Cognito App Client identifier. |
| `STORAGE_BACKEND` | Yes | `local` | `aws` | Persistence mode (`local` or `aws`). |
| `LOCAL_DB_PATH` | If local | `data/finguard.db` | `data/finguard.db` | Path to embedded SQLite database. |
| `DYNAMODB_TABLE_PREFIX`| If AWS | `finguard` | `finguard` | Table prefix for DynamoDB user and usage tables. |
| `S3_BUCKET_NAME` | If S3 | `""` | `finguard-ai-private-reports` | Private bucket name for explicit saved reports. |
| `S3_PRESIGNED_EXPIRY_SECONDS`| No | `3600` | `3600` | Time-to-live for presigned report download URLs. |

### Frontend (`frontend/.env`)
| Variable | Required | Default (Dev) | Production Example | Description |
| :--- | :---: | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000/api` | `https://api.finguard.yourdomain.com/api` | Base URL of the backend REST API. |

---

## 4. Least-Privilege IAM Policy Specifications

### A. Backend Execution Role (`FinGuardBackendRole`)
Attach this policy to your AWS App Runner instance role or ECS Task Execution Role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBTableAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/finguard_users",
        "arn:aws:dynamodb:*:*:table/finguard_users/index/*",
        "arn:aws:dynamodb:*:*:table/finguard_usage_events",
        "arn:aws:dynamodb:*:*:table/finguard_audit_logs"
      ]
    },
    {
      "Sid": "PrivateReportsS3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::finguard-ai-private-reports",
        "arn:aws:s3:::finguard-ai-private-reports/*"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/apprunner/*"
    }
  ]
}
```

### B. S3 Private Reports Bucket Policy (`finguard-ai-private-reports`)
Enforces TLS 1.2+ encrypted transport and Server-Side Encryption (`AES256`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceTLSRequestsOnly",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::finguard-ai-private-reports",
        "arn:aws:s3:::finguard-ai-private-reports/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "EnforceServerSideEncryption",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::finguard-ai-private-reports/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

---

## 5. Deployment Instructions

### A. Frontend Deployment (Amazon S3 + CloudFront CDN)

1. **Build the Production Bundle**:
   ```bash
   cd frontend
   npm run build
   # Outputs optimized static artifacts to frontend/dist/
   ```

2. **Create Private S3 Bucket for Static Assets**:
   ```bash
   aws s3api create-bucket \
       --bucket finguard-frontend-static \
       --region us-east-1
   
   # Enable Block Public Access (all 4 flags true)
   aws s3api put-public-access-block \
       --bucket finguard-frontend-static \
       --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
   ```

3. **Upload Dist Files to S3**:
   ```bash
   aws s3 sync dist/ s3://finguard-frontend-static/ --delete
   ```

4. **Create CloudFront Distribution with Origin Access Control (OAC)**:
   - Origin: `finguard-frontend-static.s3.amazonaws.com`
   - Viewer Protocol Policy: **Redirect HTTP to HTTPS**
   - Allowed HTTP Methods: `GET, HEAD`
   - Custom Error Responses (SPA routing):
     - HTTP Error Code: `403` and `404`
     - Response Page Path: `/index.html`
     - HTTP Response Code: `200`

---

### B. Backend Deployment (AWS App Runner)

1. **Build and Tag Container Image**:
   ```bash
   cd backend
   docker build -t finguard-backend:latest .
   ```

2. **Authenticate with Amazon ECR and Push Image**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
   
   docker tag finguard-backend:latest <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/finguard-backend:latest
   docker push <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/finguard-backend:latest
   ```

3. **Create AWS App Runner Service**:
   - Source: ECR Container image `<YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/finguard-backend:latest`
   - Port: `8000`
   - Health Check Path: `/api/health`
   - Instance configuration: `1 vCPU, 2 GB Memory`
   - Instance IAM Role: Attach `FinGuardBackendRole`
   - Environment Variables:
     - `APP_ENV=production`
     - `CORS_ORIGINS=https://finguard.yourdomain.com`
     - `AUTH_PROVIDER=cognito`
     - `COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx`
     - `COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx`
     - `STORAGE_BACKEND=aws`
     - `DYNAMODB_TABLE_PREFIX=finguard`
     - `S3_BUCKET_NAME=finguard-ai-private-reports`

---

## 6. Verification Checklist Prior to Deployment

Verify the following in your AWS account before creating resources:
- [ ] **AWS Account Free Tier Status**: Check whether your AWS account is within the first 12 months for Free Tier allowances.
- [ ] **Default AWS Region**: Ensure all resources (Cognito, DynamoDB, S3, App Runner) reside in the same region (e.g. `us-east-1`) to avoid cross-region data transfer fees.
- [ ] **Billing Alerts Enabled**: Verify that billing alerts are enabled in AWS Billing Preferences.
- [ ] **Service Quotas**: Check that default ECR and App Runner service quotas are active in your region.
- [ ] **Payment Method Verified**: Confirm an active payment card is linked in AWS Billing to prevent unexpected service suspension.

---

## 7. Cost Estimates & Free Tier Allowances

### Services That May Incur Charges:
| Service | Free Tier Allowance | Potential Costs if Exceeded | Expected Project Monthly Cost |
| :--- | :--- | :--- | :--- |
| **AWS App Runner** | None (paid per provisioned container hour) | ~$0.007 / GB-hour memory + ~$0.064 / vCPU-hour active | **~$5.00 – $12.00 / month** (automatic pause when idle reduces cost) |
| **Amazon Cognito** | 50,000 Monthly Active Users (MAU) free | $0.0055 per user after 50k | **$0.00** |
| **Amazon DynamoDB** | 25 GB storage + 25 WCU / 25 RCU free forever | $0.25 per GB / mo | **$0.00** |
| **Amazon S3** | 5 GB storage + 20,000 GET / 2,000 PUT free (12 mo) | $0.023 per GB / mo | **<$0.10** |
| **Amazon CloudFront**| 1 TB data transfer out free every month | $0.085 per GB | **$0.00** |

---

## 8. Billing, Budget Alert & Teardown Checklist

### Set Up an AWS Budget Alert ($5.00 limit)
1. Go to **AWS Billing & Cost Management** $\rightarrow$ **Budgets**.
2. Click **Create budget** $\rightarrow$ Select **Cost budget (Recommended)**.
3. Budget name: `FinGuard-AI-Monthly-Alert`.
4. Budgeted amount: **$5.00** / month.
5. Notification threshold: Email notification at **80% ($4.00)** and **100% ($5.00)**.

### Teardown / Cleanup Checklist
When project evaluation concludes, execute the following steps to ensure zero ongoing charges:
```bash
# 1. Delete App Runner service
aws apprunner delete-service --service-arn <SERVICE_ARN>

# 2. Empty and delete private reports S3 bucket
aws s3 rm s3://finguard-ai-private-reports --recursive
aws s3api delete-bucket --bucket finguard-ai-private-reports

# 3. Empty and delete frontend static S3 bucket
aws s3 rm s3://finguard-frontend-static --recursive
aws s3api delete-bucket --bucket finguard-frontend-static

# 4. Disable and delete CloudFront distribution
aws cloudfront get-distribution-config --id <DIST_ID>
aws cloudfront delete-distribution --id <DIST_ID> --if-match <ETAG>

# 5. Delete DynamoDB tables
aws dynamodb delete-table --table-name finguard_users
aws dynamodb delete-table --table-name finguard_usage_events
aws dynamodb delete-table --table-name finguard_audit_logs

# 6. Delete Cognito User Pool
aws cognito-idp delete-user-pool --user-pool-id <USER_POOL_ID>
```
