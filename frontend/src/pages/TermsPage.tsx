import { AlertTriangle } from 'lucide-react';

export function TermsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Terms and Conditions</h1>
        <p>
          Important disclaimers, educational terms of service, and liability limitations for the
          FinGuard AI demonstration platform.
        </p>
      </header>

      {/* Purpose */}
      <section className="mb-2">
        <p className="section-label">1. Educational & Academic Demonstration Only</p>
        <div className="card">
          <div className="card-body">
            <p className="card-text mb-1">
              FinGuard AI is developed exclusively for educational and academic evaluation purposes
              by a student team in India. It is provided on an &quot;AS IS&quot; and &quot;AS AVAILABLE&quot;
              basis without warranties of any kind.
            </p>
            <p className="card-text">
              The project is designed to compare machine learning architectures (XGBoost, Multilayer
              Perceptron, Autoencoder) under synthetic and benchmark dataset conditions. It does not
              constitute a commercial banking solution.
            </p>
          </div>
        </div>
      </section>

      {/* Non-Production Disclaimer */}
      <section className="mb-2">
        <p className="section-label">2. Disclaimer of Production Fraud Prevention</p>
        <div className="card">
          <div className="card-body">
            <div className="alert alert-warn mb-2">
              <AlertTriangle size={18} />
              <div>
                <strong>Strict Disclaimer: </strong>
                <span>
                  Do not use FinGuard AI to authorize, decline, or adjudicate actual live financial
                  transactions, credit card authorizations, or real-time banking transfers.
                </span>
              </div>
            </div>
            <p className="card-text mb-1">
              The models exposed in this interface have not been stress-tested against active
              adversarial spoofing, distributed fraud syndicates, or dynamic concept drift in live
              financial pipelines.
            </p>
            <p className="card-text">
              No warranty is made regarding accuracy, recall, false positive rates, or latency when
              applied to transactions outside the specific training splits used in this research.
            </p>
          </div>
        </div>
      </section>

      {/* Limitation of Liability */}
      <section className="mb-2">
        <p className="section-label">3. Limitation of Liability</p>
        <div className="card">
          <div className="card-body">
            <p className="card-text">
              Under no circumstances shall the developers, academic institution, or contributors be
              held liable for any direct, indirect, incidental, special, consequential, or punitive
              damages, including but not limited to loss of capital, chargebacks, banking fines,
              regulatory penalties, or data loss arising from the use or inability to use this software.
            </p>
          </div>
        </div>
      </section>

      {/* Intellectual Property & Open Code */}
      <section>
        <p className="section-label">4. Intellectual Property & Citation</p>
        <div className="card">
          <div className="card-body">
            <p className="card-text mb-1">
              Code and architecture artifacts in this repository are maintained for peer review and
              academic evaluation. Benchmark datasets used:
            </p>
            <ul
              style={{
                paddingLeft: '1.25rem',
                color: 'var(--fg-700)',
                fontSize: '0.867rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.35rem',
              }}
            >
              <li>Credit Card Fraud Detection Dataset (anonymized tabular features)</li>
              <li>
                PaySim: A financial mobile money simulator for fraud detection (Lopez-Rojas et al.)
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
