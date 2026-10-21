import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowRight, Info } from 'lucide-react';
import { api } from '../services/api';
import type { ModelRegistryEntry } from '../types';
import { DATASET_LABELS } from '../types';
import { Loading, ErrorBox, EmptyState } from '../components/StateDisplays';

/* ─── Models List Page ─── */
export function ModelsPage() {
  const [models, setModels] = useState<ModelRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    api.getModels()
      .then((r) => { setModels(r.models); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  const filtered = filter === 'all' ? models : models.filter((m) => m.dataset_id === filter);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Model Registry</h1>
        <p>All trained models, their feature schemas, decision thresholds, and recorded evaluation metrics.</p>
      </header>

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      {!loading && !error && (
        <>
          {/* Dedicated Model Family Navigation */}
          <section className="mb-2">
            <p className="section-label">Model Families</p>
            <div className="grid-3 mb-2">
              <Link to="/models/xgboost" className="card" style={{ textDecoration: 'none' }}>
                <div className="card-body">
                  <span className="badge badge-blue mb-1">Model 1</span>
                  <h3 className="card-title">XGBoost</h3>
                  <p className="card-text mb-1">Gradient boosted decision tree ensemble with fraud probability scoring.</p>
                  <span className="text-xs text-muted flex items-center gap-1">Dedicated page & metrics <ArrowRight size={12} /></span>
                </div>
              </Link>
              <Link to="/models/mlp" className="card" style={{ textDecoration: 'none' }}>
                <div className="card-body">
                  <span className="badge badge-blue mb-1">Model 2</span>
                  <h3 className="card-title">Multilayer Perceptron (MLP)</h3>
                  <p className="card-text mb-1">Deep feed-forward neural network with normalized inputs and dropout.</p>
                  <span className="text-xs text-muted flex items-center gap-1">Dedicated page & metrics <ArrowRight size={12} /></span>
                </div>
              </Link>
              <Link to="/models/autoencoder" className="card" style={{ textDecoration: 'none' }}>
                <div className="card-body">
                  <span className="badge badge-blue mb-1">Model 3</span>
                  <h3 className="card-title">Autoencoder</h3>
                  <p className="card-text mb-1">Unsupervised anomaly detector scoring reconstruction error (MSE).</p>
                  <span className="text-xs text-muted flex items-center gap-1">Dedicated page & metrics <ArrowRight size={12} /></span>
                </div>
              </Link>
            </div>
          </section>

          <div className="toolbar">
            <select className="form-select" style={{maxWidth:260}} value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">All Datasets</option>
              <option value="credit_card_dataset_1">Credit Card Fraud Detection</option>
              <option value="paysim_dataset_2">PaySim Synthetic Mobile Money</option>
            </select>
            <span className="text-sm text-muted">{filtered.length} model{filtered.length !== 1 ? 's' : ''}</span>
          </div>

          <div className="grid-2">
            {filtered.map((m) => (
              <div key={m.model_id} className="card" style={{opacity: m.is_available ? 1 : 0.6}}>
                <div className="card-body">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="card-title" style={{marginBottom:0}}>{m.model_name}</h3>
                    <span className={`badge ${m.is_available ? 'badge-green' : 'badge-gray'}`}>
                      {m.is_available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                  <p className="text-xs text-muted mb-1">
                    {DATASET_LABELS[m.dataset_id] ?? m.dataset_id} · {m.model_family}
                  </p>
                  <p className="card-text mb-1">
                    Score type: {m.score_type === 'fraud_probability' ? 'Fraud Probability' : 'Reconstruction Error'}
                    {m.threshold != null && <> · Threshold: <code>{m.threshold.toFixed(6)}</code></>}
                  </p>
                  {m.evaluation_metrics && (
                    <div className="flex flex-wrap gap-1 mb-1">
                      {m.evaluation_metrics.f1_score != null && <span className="badge badge-blue">F1 {m.evaluation_metrics.f1_score.toFixed(4)}</span>}
                      {m.evaluation_metrics.pr_auc != null && <span className="badge badge-blue">PR-AUC {m.evaluation_metrics.pr_auc.toFixed(4)}</span>}
                      {m.evaluation_metrics.roc_auc != null && <span className="badge badge-blue">ROC-AUC {m.evaluation_metrics.roc_auc.toFixed(4)}</span>}
                    </div>
                  )}
                  {!m.is_available && m.unavailable_reason && (
                    <div className="alert alert-warn mt-1" style={{padding:'0.4rem 0.6rem'}}>
                      <Info size={14} />
                      <span className="text-xs">{m.unavailable_reason}</span>
                    </div>
                  )}
                  <div className="mt-1">
                    <Link to={`/models/${m.model_id}`} className="btn btn-sm">
                      View Details <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Model Detail Page ─── */
export function ModelDetailPage() {
  const { modelId } = useParams<{ modelId: string }>();
  const [model, setModel] = useState<ModelRegistryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!modelId) return;
    api.getModel(modelId)
      .then((m) => { setModel(m); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [modelId]);

  if (loading) return <div className="page"><Loading /></div>;
  if (error) return <div className="page"><ErrorBox message={error} /></div>;
  if (!model) return <div className="page"><EmptyState message="Model not found." /></div>;

  const em = model.evaluation_metrics;
  const isAE = model.model_family === 'Autoencoder';

  return (
    <div className="page">
      <header className="page-header">
        <div className="flex items-center gap-1 mb-1">
          <h1 style={{marginBottom:0}}>{model.model_name}</h1>
          <span className={`badge ${model.is_available ? 'badge-green' : 'badge-gray'}`}>
            {model.is_available ? 'Available' : 'Unavailable'}
          </span>
        </div>
        <p>{DATASET_LABELS[model.dataset_id] ?? model.dataset_id}</p>
      </header>

      {!model.is_available && model.unavailable_reason && (
        <div className="alert alert-warn mb-2">
          <Info size={16} />
          <span>{model.unavailable_reason}</span>
        </div>
      )}

      {/* Configuration */}
      <section className="mb-2">
        <p className="section-label">Configuration</p>
        <div className="card">
          <div className="card-body">
            <div className="grid-2">
              <div className="result-row"><span className="result-label">Model ID</span><span className="result-value">{model.model_id}</span></div>
              <div className="result-row"><span className="result-label">Model Family</span><span className="result-value">{model.model_family}</span></div>
              <div className="result-row"><span className="result-label">Dataset ID</span><span className="result-value">{model.dataset_id}</span></div>
              <div className="result-row"><span className="result-label">Target Column</span><span className="result-value">{model.target_column}</span></div>
              <div className="result-row"><span className="result-label">Artifact File</span><span className="result-value">{model.model_artifact_filename}</span></div>
              <div className="result-row"><span className="result-label">Scaler File</span><span className="result-value">{model.scaler_artifact_filename ?? 'None'}</span></div>
              <div className="result-row"><span className="result-label">Score Type</span><span className="result-value">{isAE ? 'Reconstruction Error (Anomaly Score)' : 'Fraud Probability'}</span></div>
              <div className="result-row"><span className="result-label">Threshold</span><span className="result-value">{model.threshold != null ? model.threshold.toFixed(8) : 'Not configured'}</span></div>
            </div>
          </div>
        </div>
      </section>

      {/* Decision Rule */}
      <section className="mb-2">
        <p className="section-label">Decision Rule</p>
        <div className="card">
          <div className="card-body">
            <p className="card-text">{model.prediction_rule}</p>
            {isAE && (
              <p className="text-xs text-muted mt-1">
                The autoencoder is trained on legitimate-only transactions. Reconstruction error
                quantifies how poorly the model can reproduce a transaction — higher error suggests
                the transaction deviates from learned normal patterns. This value is not a probability.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Required Features */}
      <section className="mb-2">
        <p className="section-label">Required Input Features</p>
        <div className="card">
          <div className="card-body">
            <p className="text-xs text-muted mb-1">
              Raw features expected from the user. Internal encoding is handled by the backend.
            </p>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>#</th><th>Feature Name</th></tr></thead>
                <tbody>
                  {model.required_raw_features.map((f, i) => (
                    <tr key={f}><td>{i + 1}</td><td className="table-mono">{f}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* Evaluation Metrics */}
      {em && (
        <section className="mb-2">
          <p className="section-label">Recorded Evaluation Metrics</p>
          <p className="text-xs text-muted mb-1">
            These metrics were computed during model training and saved in {model.metrics_filename}.
            They describe performance on the original held-out test split, not on user-uploaded data.
          </p>
          <div className="grid-3">
            {em.accuracy != null && <div className="card"><div className="stat"><p className="stat-label">Accuracy</p><p className="stat-value">{(em.accuracy * 100).toFixed(2)}%</p></div></div>}
            {em.precision != null && <div className="card"><div className="stat"><p className="stat-label">Precision</p><p className="stat-value">{em.precision.toFixed(4)}</p></div></div>}
            {em.recall != null && <div className="card"><div className="stat"><p className="stat-label">Recall</p><p className="stat-value">{em.recall.toFixed(4)}</p></div></div>}
            {em.f1_score != null && <div className="card"><div className="stat"><p className="stat-label">F1 Score</p><p className="stat-value">{em.f1_score.toFixed(4)}</p></div></div>}
            {em.roc_auc != null && <div className="card"><div className="stat"><p className="stat-label">ROC-AUC</p><p className="stat-value">{em.roc_auc.toFixed(4)}</p></div></div>}
            {em.pr_auc != null && <div className="card"><div className="stat"><p className="stat-label">PR-AUC</p><p className="stat-value">{em.pr_auc.toFixed(4)}</p></div></div>}
          </div>

          {em.confusion_matrix && (
            <div className="card mt-1">
              <div className="card-body">
                <p className="card-title">Confusion Matrix</p>
                <div className="table-wrap" style={{maxWidth:340}}>
                  <table className="table">
                    <thead><tr><th></th><th>Predicted Legit</th><th>Predicted Fraud</th></tr></thead>
                    <tbody>
                      <tr><td className="text-xs" style={{fontWeight:600}}>Actual Legit</td><td className="table-mono">{em.confusion_matrix[0][0].toLocaleString()}</td><td className="table-mono">{em.confusion_matrix[0][1].toLocaleString()}</td></tr>
                      <tr><td className="text-xs" style={{fontWeight:600}}>Actual Fraud</td><td className="table-mono">{em.confusion_matrix[1][0].toLocaleString()}</td><td className="table-mono">{em.confusion_matrix[1][1].toLocaleString()}</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Actions */}
      {model.is_available && (
        <section>
          <div className="flex gap-1">
            <Link to={`/transaction?model=${model.model_id}&dataset=${model.dataset_id}`} className="btn btn-primary">
              Screen a Transaction
            </Link>
            <Link to={`/csv?model=${model.model_id}&dataset=${model.dataset_id}`} className="btn">
              Batch CSV Analysis
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
