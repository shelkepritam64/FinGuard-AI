import { Database, AlertTriangle } from 'lucide-react';

export function AboutPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Project Information & Academic Scope</h1>
        <p>
          FinGuard AI is an educational transaction fraud-risk screening application developed by a
          team of two engineering students in India.
        </p>
      </header>

      {/* Origin & Educational Context */}
      <section className="mb-2">
        <p className="section-label">Academic Context</p>
        <div className="card">
          <div className="card-body">
            <h3 className="card-title">Educational Deep Learning & Machine Learning Project</h3>
            <p className="card-text mb-1">
              This system was designed as an undergraduate comparative study exploring how traditional
              gradient boosting and deep neural architectures handle severe class imbalance in
              financial transaction streams.
            </p>
            <p className="card-text">
              The project prioritizes reproducible methodology, transparent preprocessing pipelines,
              and explicit metric reporting over marketing claims or commercial deployment assertions.
            </p>
          </div>
        </div>
      </section>

      {/* Dataset Realities */}
      <section className="mb-2">
        <p className="section-label">Datasets & Scope</p>
        <div className="grid-2">
          <div className="card">
            <div className="card-body">
              <div className="flex items-center gap-1 mb-1">
                <Database size={18} color="var(--blue-600)" />
                <h3 className="card-title" style={{ marginBottom: 0 }}>
                  Credit Card Fraud Dataset
                </h3>
              </div>
              <p className="card-text mb-1">
                Contains 7 engineered numerical features capturing geographic transaction distance,
                pricing ratios relative to median purchases, and card-present security indicators.
              </p>
              <p className="text-xs text-muted">
                Target: <code>fraud</code> (Binary: 0 for legitimate, 1 for fraudulent).
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center gap-1 mb-1">
                <Database size={18} color="var(--blue-600)" />
                <h3 className="card-title" style={{ marginBottom: 0 }}>
                  PaySim Synthetic Mobile Money
                </h3>
              </div>
              <p className="card-text mb-1">
                Agent-based simulation of mobile financial transactions based on a sample of real logs
                from a financial service (Lopez-Rojas et al., 2016).
              </p>
              <div className="alert alert-warn mt-1">
                <AlertTriangle size={16} />
                <span className="text-xs">
                  PaySim is synthetic mobile-money simulation data, not real Indian UPI transaction data.
                  It does not contain Indian banking identifiers such as Virtual Payment Addresses
                  (VPAs), IFSC codes, bank handles, or NPCI settlement codes.
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Model Families Evaluated */}
      <section className="mb-2">
        <p className="section-label">Model Families</p>
        <div className="grid-3">
          <div className="card">
            <div className="card-body">
              <h3 className="card-title">1. XGBoost</h3>
              <p className="card-text">
                Ensemble gradient boosting with tree learners. Highly resilient to non-linear feature
                scales and structured tabular attributes.
              </p>
              <p className="text-xs text-muted mt-1">Outputs calibrated fraud probability.</p>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <h3 className="card-title">2. MLP Neural Network</h3>
              <p className="card-text">
                Fully connected deep neural network with batch normalization, ReLU hidden units, and
                dropout regularization.
              </p>
              <p className="text-xs text-muted mt-1">Outputs sigmoid fraud probability.</p>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <h3 className="card-title">3. Autoencoder</h3>
              <p className="card-text">
                Unsupervised symmetrical bottleneck network trained solely on legitimate non-fraud
                transactions.
              </p>
              <p className="text-xs text-muted mt-1">
                Outputs reconstruction error (MSE), quantifying anomaly deviation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Limitations & Disclaimers */}
      <section className="mb-2">
        <p className="section-label">Limitations & Non-Production Notice</p>
        <div className="card">
          <div className="card-body">
            <ul
              style={{
                paddingLeft: '1.25rem',
                color: 'var(--fg-700)',
                fontSize: '0.867rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <li>
                <strong>No Guaranteed Fraud Prevention:</strong> These models serve as an educational
                screening demonstration and do not guarantee detection of real-world adversarial attacks.
              </li>
              <li>
                <strong>Concept Drift:</strong> Real-world fraud vectors adapt dynamically; static
                models evaluated on static benchmark splits will experience rapid performance decay
                in live production settings.
              </li>
              <li>
                <strong>Synthetic Data Limitations:</strong> Findings on the PaySim dataset reflect
                the underlying simulation parameters of Lopez-Rojas et al. and must not be extrapolated
                to Indian Unified Payments Interface (UPI) systems.
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Technical Architecture */}
      <section>
        <p className="section-label">Architecture Stack</p>
        <div className="card">
          <div className="card-body">
            <div className="grid-2">
              <div className="result-row">
                <span className="result-label">Frontend</span>
                <span className="result-value">React, Vite, TypeScript, Pure CSS</span>
              </div>
              <div className="result-row">
                <span className="result-label">Backend</span>
                <span className="result-value">Python FastAPI, Pydantic v2</span>
              </div>
              <div className="result-row">
                <span className="result-label">Data Science & ML</span>
                <span className="result-value">Scikit-Learn, XGBoost, TensorFlow / Keras, Pandas</span>
              </div>
              <div className="result-row">
                <span className="result-label">Design Language</span>
                <span className="result-value">Restrained Fintech Analytics Design System</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
