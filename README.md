# FinGuard AI

**FinGuard AI** is an educational transaction fraud-risk screening application developed by a team of two university students in India. The application evaluates machine learning and deep learning models across two benchmark datasets to detect anomalous and fraudulent financial transactions.

---

## 1. Project Context & Datasets

1. **Credit Card Fraud Detection (`dataset/credit_card_trans_data.csv`)**
   - Target Column: `fraud` (0 = Legitimate, 1 = Fraudulent)
   - Features: 7 tabular transaction metrics (distance from home, distance from last transaction, ratio to median price, chip/PIN/online indicators).
2. **PaySim Synthetic Financial Transactions (`dataset/paysim_dataset.csv`)**
   - Target Column: `isFraud` (0 = Legitimate, 1 = Fraudulent)
   - Features: `step`, `amount`, and one-hot encoded transaction `type` (`CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER`).
   - *Important Notice:* PaySim is an agent-based synthetic simulation of mobile money in an African context (Lopez-Rojas et al.). It is **not** real Indian Unified Payments Interface (UPI) data.

---

## 2. Model Families Evaluated
- **XGBoost:** Gradient boosted tree classification (`xgboost_model1_1.pkl` and `xgboost_model_2.pkl`).
- **MLP (Multilayer Perceptron):** Supervised deep neural network (`mlp_model_1.keras` and `mlp_model_2.keras`).
- **Autoencoder:** Unsupervised reconstruction error anomaly detection (`autoencoder_model_1.keras` and `autoencoder_model_2.keras`).

---

## 3. Directory Layout

```
FinGuard-AI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entrypoint
│   │   ├── config.py            # Environment-driven settings (Pydantic)
│   │   ├── api/                 # Endpoint routers (/api/health, etc.)
│   │   ├── core/                # Core utilities
│   │   ├── schemas/             # Request & response schemas
│   │   └── services/            # Preprocessors and model inference
│   ├── tests/                   # Pytest suite
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Screen views (HomePage, etc.)
│   │   ├── services/            # API client and networking
│   │   ├── types/               # TypeScript domain definitions
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css            # Dark-mode styling system
│   ├── public/                  # Static assets (favicon, etc.)
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
│
├── docs/                        # Model audit, architecture, and disclaimers
├── .gitignore
├── .env.example
└── README.md
```

---

## 4. Local Setup & Execution

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ and npm (tested on Node 24 & npm 11)

### A. Running the Backend Service

1. Navigate to the backend directory:
   ```bash
   cd FinGuard-AI/backend
   ```
2. (Optional) Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
5. Run the backend tests:
   ```bash
   python -m pytest tests/
   ```
6. Start the development server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   The backend API will be available at `http://127.0.0.1:8000/api/health` and docs at `http://127.0.0.1:8000/docs`.

---

### B. Running the Frontend Application

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd FinGuard-AI/frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Copy the frontend environment template:
   ```bash
   cp .env.example .env
   ```
4. Run the frontend build validation:
   ```bash
   npm run build
   ```
5. Start the Vite local development server:
   ```bash
   npm run dev
   ```
   The frontend application will be accessible at `http://localhost:5173`.

---

## 5. Security & Privacy Guardrails
- All model inference runs strictly locally in-memory on the host machine.
- No transaction data or credit card numbers are transmitted to external cloud databases.
- Original notebooks, training runs, and dataset CSV files are preserved read-only and never modified by the application.
