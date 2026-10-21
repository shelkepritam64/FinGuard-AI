# FinGuard AI — Model Audit Report

## 1. Overview
FinGuard AI is an educational transaction fraud-risk screening application developed by two students in India. This audit provides verified findings from the existing repository and Jupyter notebooks.

## 2. Datasets
1. **Credit Card Fraud Detection (`dataset/credit_card_trans_data.csv`)**
   - **Target Column:** `fraud` (0 = Legitimate, 1 = Fraudulent).
   - **Raw Features:** `distance_from_home`, `distance_from_last_transaction`, `ratio_to_median_purchase_price`, `repeat_retailer`, `used_chip`, `used_pin_number`, `online_order`.
   - **Preprocessing:** All 7 features are numeric. XGBoost uses raw values; MLP and Autoencoder use `StandardScaler`.
2. **PaySim Synthetic Financial Transactions (`dataset/paysim_dataset.csv`)**
   - **Target Column:** `isFraud` (0 = Legitimate, 1 = Fraudulent).
   - **Features Used:** `step`, `amount`, and one-hot encoded `type` (`type_CASH_IN`, `type_CASH_OUT`, `type_DEBIT`, `type_PAYMENT`, `type_TRANSFER`). Total: 7 features.
   - **Important Domain Note:** PaySim is an agent-based simulation of mobile money in an African context (Lopez-Rojas et al.), not Indian UPI data. UPI transactions involve proprietary bank and NPCI network architectures not present in PaySim.

## 3. Model Families & Verified Artifacts
- **XGBoost:**
  - Dataset 1: `models/credit_card_dataset_1/xgboost_model1_1.pkl` (threshold: 0.4721)
  - Dataset 2: `models/paysim_dataset_2/xgboost_model_2.pkl` (threshold: 0.5249; best iteration: 0)
- **MLP Neural Network:**
  - Dataset 1: `models/credit_card_dataset_1/mlp_model_1.keras` with `scaler_neural_networks_1.pkl` (threshold: 0.9056)
  - Dataset 2: `models/paysim_dataset_2/mlp_model_2.keras` with `scaler_neural_networks_2.pkl` (threshold: 0.9926)
- **Autoencoder Anomaly Detection:**
  - Dataset 1: `models/credit_card_dataset_1/autoencoder_model_1.keras` with `scaler_autoencoder_1.pkl` (MSE threshold: 0.00632)
  - Dataset 2: `models/paysim_dataset_2/autoencoder_model_2.keras` with `scaler_autoencoder_2.pkl` (MSE threshold: 0.0790)

## 4. Operational Guardrails
- Models are evaluated using validation thresholds stored in metadata JSON files.
- Original model artifacts are treated as immutable read-only assets.
