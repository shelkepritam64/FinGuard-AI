# FinGuard AI — System Architecture

## 1. Architectural Principles
FinGuard AI is designed with the following core architectural decisions:
- **Local & Lightweight:** Runs completely offline on student laptops without cloud database dependencies or external paid APIs.
- **Strict Immutability:** Pre-trained notebook models, metrics, and dataset files remain untouched in their original directories.
- **Decoupled Client-Server:** Modern single-page frontend (React + TypeScript + Vite) communicating over REST with a FastAPI backend.
- **Dynamic Configuration:** File paths and service endpoints are driven by environment variables (`.env`), not hardcoded strings.

## 2. Component Diagram

```
+-------------------------------------------------------+
|                FinGuard AI Frontend                   |
|        (React 19 + TypeScript + Vite + CSS)           |
|                                                       |
|  - Dataset Selector (Credit Card vs PaySim)           |
|  - Model Family Selector (XGBoost / MLP / Autoencoder)|
|  - Real-time Risk Verdict & Threshold Comparison      |
+---------------------------+---------------------------+
                            | HTTP / JSON
                            v
+-------------------------------------------------------+
|                 FastAPI Backend Service               |
|                                                       |
|  - /api/health (System status & path validation)      |
|  - /api/models (Dynamic metadata & test metrics)      |
|  - /api/predict (Preprocessing & multi-model inference)
+---------------------------+---------------------------+
                            | Read-Only File I/O
                            v
+-------------------------------------------------------+
|              Original Project Artifacts               |
|                                                       |
|  - models/credit_card_dataset_1/                      |
|  - models/paysim_dataset_2/                           |
+-------------------------------------------------------+
```

## 3. Data & Feature Preprocessing Strategy
- **Credit Card (Dataset 1):** Ingests 7 numerical features. Scaled via `StandardScaler` for neural models; raw inputs for tree models.
- **PaySim (Dataset 2):** Encodes user-provided transaction `type` into 5 one-hot columns and combines them with `step` and `amount` to create the exact 7-feature vector expected by the models.
- **Autoencoder Inference:** Calculates Mean Squared Reconstruction Error ($\text{MSE}$) between scaled inputs and reconstructed representations, comparing against empirical anomaly thresholds.
