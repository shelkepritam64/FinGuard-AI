import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Cpu, Search, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import type { ModelRegistryEntry } from '../types';
import { DATASET_LABELS } from '../types';
import { Loading, ErrorBox } from '../components/StateDisplays';

export function HomePage() {
  const [models, setModels] = useState<ModelRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getModels()
      .then((r) => { setModels(r.models); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  const available = models.filter((m) => m.is_available);

  return (
    <div className="page">
      {/* Hero — factual, no marketing copy */}
      <header className="page-header">
        <h1>Transaction Fraud-Risk Screening</h1>
        <p>
          FinGuard AI evaluates financial transactions against pre-trained machine
          learning models and returns a risk screening result. This is an educational
          research project — not a production fraud prevention system.
        </p>
      </header>

      {loading && <Loading message="Connecting to backend…" />}
      {error && <ErrorBox message={`Backend unavailable: ${error}`} />}

      {/* Problem Statement */}
      {!loading && !error && (
        <>
          <section className="mb-2">
            <p className="section-label">Problem</p>
            <div className="card">
              <div className="card-body">
                <p className="card-text">
                  Financial fraud costs billions annually worldwide. Automated screening systems
                  can flag anomalous transactions for human review before funds are lost.
                  This project explores three model families — gradient boosted trees, neural
                  network classifiers, and unsupervised anomaly detectors — across two
                  benchmark datasets to evaluate how each approach performs under realistic
                  class-imbalance conditions.
                </p>
              </div>
            </div>
          </section>

          {/* Datasets */}
          <section className="mb-2">
            <p className="section-label">Datasets</p>
            <div className="grid-2">
              <div className="card">
                <div className="card-body">
                  <h3 className="card-title">Credit Card Fraud Detection</h3>
                  <p className="card-text">
                    Contains 7 anonymised transaction features (distance metrics,
                    merchant indicators, payment method flags) with a binary
                    fraud label. All features are numeric.
                  </p>
                  <p className="text-xs text-muted mt-1">
                    Target column: <code>fraud</code> · Dataset ID: <code>credit_card_dataset_1</code>
                  </p>
                </div>
              </div>
              <div className="card">
                <div className="card-body">
                  <h3 className="card-title">PaySim Synthetic Mobile Money</h3>
                  <p className="card-text">
                    Agent-based simulation of mobile money transactions (Lopez-Rojas et al.).
                    Uses step, amount, and transaction type features.
                  </p>
                  <div className="alert alert-warn mt-1" style={{padding:'0.5rem 0.75rem'}}>
                    <span className="text-xs">
                      PaySim is synthetic data, not real Indian UPI transaction data.
                      It does not contain UPI-specific identifiers such as VPAs,
                      IFSC codes, or NPCI response fields.
                    </span>
                  </div>
                  <p className="text-xs text-muted mt-1">
                    Target column: <code>isFraud</code> · Dataset ID: <code>paysim_dataset_2</code>
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Model Families */}
          <section className="mb-2">
            <p className="section-label">Model Families</p>
            <div className="grid-3">
              <Link to="/models/xgboost" className="card" style={{ textDecoration: 'none' }}>
                <div className="card-body">
                  <div className="flex items-center gap-1 mb-1">
                    <BarChart3 size={18} color="var(--blue-600)" />
                    <h3 className="card-title" style={{marginBottom:0}}>XGBoost</h3>
                  </div>
                  <p className="card-text mb-1">
                    Gradient boosted decision trees optimised with early stopping.
                    Returns a fraud probability score.
                  </p>
                  <span className="text-xs text-muted flex items-center gap-1">View Model 1 details <ArrowRight size={12} /></span>
                </div>
              </Link>
              <Link to="/models/mlp" className="card" style={{ textDecoration: 'none' }}>
                <div className="card-body">
                  <div className="flex items-center gap-1 mb-1">
                    <Cpu size={18} color="var(--blue-600)" />
                    <h3 className="card-title" style={{marginBottom:0}}>MLP Neural Network</h3>
                  </div>
                  <p className="card-text mb-1">
                    Supervised multilayer perceptron with batch normalisation and
                    dropout. Returns a fraud probability score.
                  </p>
                  <span className="text-xs text-muted flex items-center gap-1">View Model 2 details <ArrowRight size={12} /></span>
                </div>
              </Link>
              <Link to="/models/autoencoder" className="card" style={{ textDecoration: 'none' }}>
                <div className="card-body">
                  <div className="flex items-center gap-1 mb-1">
                    <Search size={18} color="var(--blue-600)" />
                    <h3 className="card-title" style={{marginBottom:0}}>Autoencoder</h3>
                  </div>
                  <p className="card-text mb-1">
                    Unsupervised anomaly detector trained on legitimate transactions.
                    Returns a reconstruction error (anomaly score), not a probability.
                  </p>
                  <span className="text-xs text-muted flex items-center gap-1">View Model 3 details <ArrowRight size={12} /></span>
                </div>
              </Link>
            </div>
          </section>

          {/* Available Models Summary */}
          <section className="mb-2">
            <p className="section-label">Available Models ({available.length})</p>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Model ID</th>
                    <th>Dataset</th>
                    <th>Family</th>
                    <th>Score Type</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {available.map((m) => (
                    <tr key={m.model_id}>
                      <td className="table-mono">{m.model_id}</td>
                      <td>{DATASET_LABELS[m.dataset_id] ?? m.dataset_id}</td>
                      <td>{m.model_family}</td>
                      <td className="text-xs">
                        {m.score_type === 'fraud_probability' ? 'Fraud Probability' : 'Reconstruction Error'}
                      </td>
                      <td><span className="badge badge-green">Available</span></td>
                      <td>
                        <Link to={`/models/${m.model_id}`} className="btn btn-sm">
                          Details <ArrowRight size={14} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Quick Navigation */}
          <section>
            <p className="section-label">Tools</p>
            <div className="grid-3">
              <Link to="/transaction" className="card" style={{textDecoration:'none'}}>
                <div className="card-body">
                  <h3 className="card-title">Screen a Transaction</h3>
                  <p className="card-text">
                    Enter individual transaction features and get a real-time risk screening result.
                  </p>
                </div>
              </Link>
              <Link to="/csv" className="card" style={{textDecoration:'none'}}>
                <div className="card-body">
                  <h3 className="card-title">Batch CSV Analysis</h3>
                  <p className="card-text">
                    Upload a CSV file and screen all transactions against a selected model.
                  </p>
                </div>
              </Link>
              <Link to="/models" className="card" style={{textDecoration:'none'}}>
                <div className="card-body">
                  <h3 className="card-title">Model Registry</h3>
                  <p className="card-text">
                    View all model configurations, evaluation metrics, and feature schemas.
                  </p>
                </div>
              </Link>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
