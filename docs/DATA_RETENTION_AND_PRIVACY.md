# FinGuard AI — Data Retention, Storage & Privacy Architecture

## 1. Architectural Philosophy: Privacy-by-Design & Zero-Raw-Persistence

FinGuard AI is designed with strict financial data confidentiality principles:
- **Zero Raw Persistence**: Raw financial transactions, bank account numbers, customer identifiers, and uploaded CSV batch contents are processed purely in-memory and are **never permanently stored** in databases, object storage, or server logs.
- **Minimal Metadata Only**: Only anonymized aggregate usage counts (`screening_count`, `csv_count`, `flagged_count`), high-level execution timestamps, and model identifiers (`model_id`, `dataset_id`) are persisted.
- **User Ownership & Isolation**: Any explicitly saved screening report is strictly isolated to the authenticated user's private namespace (`reports/{user_id}/`). Cross-user access is blocked by cryptographic token verification and server-side authorization checks.
- **Ephemeral Uploads**: Uploaded batch CSV files are held temporarily in memory buffers, validated, processed, and immediately disposed of via `try ... finally: await file.close()`. No temporary files persist across request lifecycles or failure cases.

---

## 2. Minimal Data Layer for AWS

| Tier | AWS Service | Local Development Fallback | Purpose & Stored Attributes | Security & Isolation Controls |
| :--- | :--- | :--- | :--- | :--- |
| **Authentication & Identity** | Amazon Cognito User Pool | Local bcrypt + HS256 JWT | User identity (`sub`), email, role claims (`user` or `admin`). | RS256 JWKS verification, 2-hour sliding session token, no plain passwords. |
| **User Profiles & Usage** | Amazon DynamoDB (`finguard_users`, `finguard_usage_events`, `finguard_audit_logs`) | Local SQLite (`data/finguard.db`) | Minimal profile metadata (`id`, `email`, `role`, `status`, aggregate counters). Usage event aggregates (`model_id`, `dataset_id`, `row_count`, `flagged_count`). | On-Demand billing (free tier), IAM least-privilege, encrypted at rest via AWS KMS. Zero RDS/Aurora required. |
| **Opt-in Report Persistence** | Amazon S3 (`finguard-ai-private-reports`) | Local directory (`data/reports/{user_id}/`) | Explicitly requested exported predictions or compliance reports. | Block All Public Access, SSE-AES256 encryption, access via time-limited presigned URLs (1 hr). Strict namespace `reports/{user_id}/`. |

---

## 3. Data Classification & Retention Lifecycle

| Data Category | Examples | Storage Location | Retention Period | Deletion Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Transaction Inputs** | `distance_from_home`, `amount`, `type`, `ratio_to_median_purchase_price` | Memory only (RAM / StringIO) | **0 seconds** (duration of request only) | Discarded immediately after inference response streaming. |
| **Uploaded Batch CSVs** | Customer uploaded `.csv` transaction batches | Memory / Spooled buffer | **0 seconds** (duration of request only) | Guaranteed deletion via `finally: await file.close()`, including on malformed inputs or 4xx/5xx errors. |
| **User Account Metadata** | `email`, `full_name`, `role`, `status`, `created_at` | DynamoDB / SQLite | Account Lifetime | Permanently purged upon account deletion (`DELETE /api/auth/me`). |
| **Aggregate Usage Logs** | `model_id`, `dataset_id`, `timestamp`, `row_count`, `flagged_count` | DynamoDB / SQLite | 90 Days | Anonymized; purged or disassociated if user requests total account deletion. |
| **Audit Logs** | Admin actions (`role_change`, `status_toggle`, `delete_user`) | DynamoDB / SQLite | 365 Days | Retained for compliance; contains actor email and timestamp only, zero financial payloads. |
| **Saved Reports (Opt-in)** | User-requested batch exports | S3 / Local Reports | 30 Days (S3 Lifecycle Rule) or until deleted | Hard-deleted immediately when user deletes report or requests account deletion. |

---

## 4. File Upload Validation & Sanitization

To prevent denial-of-service, remote code execution, and data corruption, all file inputs undergo rigorous multi-stage validation:
1. **Size Enforcement**: Capped at `settings.MAX_UPLOAD_SIZE_MB` (default 10MB). Uploads exceeding this threshold are rejected with HTTP 400 before parsing.
2. **Binary Content Rejection**: Uploaded bytes are inspected for null bytes (`\x00`) and UTF-8 encoding compliance. Binary executables, images, or disguised zip files return HTTP 400.
3. **Format & Delimiter Parsing**: Parsed using strict pandas CSV stream validation. Empty CSVs or files containing zero data rows return HTTP 400.
4. **Schema & Feature Alignment**: Input columns are strictly matched against the verified model feature schema (`ordered_model_features`). Missing columns or NaN/null values return HTTP 400 with detailed schema guidance. Extra columns (such as true labels or IDs) are stripped during preprocessing and not used for inference.
5. **Path Traversal Prevention**: Filenames are sanitized using `Path(filename).name` and stripped of directory traversal tokens (`..`, `/`, `\`).

---

## 5. User Ownership & Namespace Verification

Access to persistent files and account data strictly verifies tenant ownership:
```python
# Server-side ownership guard enforced on all report operations
expected_prefix = f"reports/{current_user['id']}/"
if not report_key.startswith(expected_prefix):
    raise HTTPException(
        status_code=403,
        detail="Access denied: You do not own this storage object."
    )
```
- Users can never query, download, or delete another user's saved report.
- S3 presigned URLs are generated only after ownership verification, expiring within 3600 seconds (1 hour).

---

## 6. Account Deletion & Right-to-be-Forgotten Workflow

When a user requests account deletion (`DELETE /api/auth/me` or administrative purge):
1. **Report Purge**: All S3 objects under `reports/{user_id}/*` (or local filesystem directory) are permanently hard-deleted.
2. **Usage Purge**: Anonymized usage event associations for `user_id` are purged from the database.
3. **User Record Removal**: The user record in `users` (or DynamoDB `finguard_users`) is deleted.
4. **Audit Trail**: An administrative audit event (`action="delete_user"`) is recorded for security tracking, noting the timestamp and account email without retaining sensitive keys.

---

## 7. Amazon S3 Bucket Security Specification

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

### S3 Lifecycle Configuration (Auto-Expiration)
Configure an S3 Lifecycle rule on `finguard-ai-private-reports`:
- **Rule Name**: `ExpireSavedReportsAfter30Days`
- **Scope**: Prefix `reports/`
- **Expiration**: Expire objects 30 days after creation
- **Incomplete Multipart Uploads**: Abort after 7 days
