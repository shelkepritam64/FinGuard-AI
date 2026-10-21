import { useEffect, useState } from 'react';
import { Link, useParams, useLocation } from 'react-router-dom';
import { ArrowLeft, ArrowRight, ShieldCheck, Cpu, Search } from 'lucide-react';
import { api } from '../services/api';
import type { ModelRegistryEntry, ModelFamily } from '../types';
import { DATASET_LABELS } from '../types';
import { Loading, ErrorBox } from '../components/StateDisplays';

interface FamilyConfig {
  family: ModelFamily;
  title: string;
  subtitle: string;
  purpose: string;
  scoreDescription: string;
  evaluationLimitations: string[];
  icon: typeof ShieldCheck;
}

const FAMILY_CONFIGS: Record<string, FamilyConfig> = {
  xgboost: {
    family: 'XGBoost',
    title: 'Model 1: XGBoost Gradient Boosted Trees',
    subtitle: 'Ensemble decision-tree classifier with gradient boosting',
    purpose:
      'XGBoost builds sequential shallow decision trees where each successive tree minimizes residual prediction errors of the prior ensemble. For fraud detection, it provides high predictive precision on structured tabular tabular transaction data with non-linear feature interactions.',
    scoreDescription:
      'Fraud Probability: Outputs a calibrated probability between 0.0 and 1.0 representing the likelihood that a transaction is fraudulent. Transactions scoring above the validated decision threshold are flagged for manual compliance review.',
    evaluationLimitations: [
      'Sensitivity to severe class imbalance (often < 1% true fraud) requires careful threshold tuning rather than standard 0.5 default.',
      'Cannot naturally identify novel, unseen fraud patterns that deviate structurally from the historical training distributions.',
      'Tree boundaries are axis-aligned and can produce step-function artifacts in edge-case regions of feature space.',
    ],
    icon: ShieldCheck,
  },
  mlp: {
    family: 'MLP',
    title: 'Model 2: Multilayer Perceptron (MLP)',
    subtitle: 'Feed-forward deep neural network classifier',
    purpose:
      'The MLP maps preprocessed, scaled transaction features through multiple fully-connected dense layers with ReLU activations, batch normalization, and dropout regularization to model complex high-dimensional decision boundaries.',
    scoreDescription:
      'Fraud Probability: Emits a sigmoid output between 0.0 and 1.0 quantifying fraud likelihood. Requires standardized numerical inputs (via StandardScaler) and one-hot encoded categorical fields.',
    evaluationLimitations: [
      'Requires strict feature scaling; input outliers or out-of-distribution values can saturate activation functions.',
      'Black-box decision boundaries provide less direct feature interpretability compared to tree-based models.',
      'Prone to overfitting minor fraud clusters without dropout and batch normalization.',
    ],
    icon: Cpu,
  },
  autoencoder: {
    family: 'Autoencoder',
    title: 'Model 3: Autoencoder Anomaly Detector',
    subtitle: 'Unsupervised bottleneck reconstruction neural network',
    purpose:
      'The Autoencoder is trained strictly on legitimate (non-fraudulent) transactions to learn the compact manifold of normal financial activity. When presented with anomalous fraudulent transactions, the network fails to reconstruct them accurately, producing an elevated reconstruction error.',
    scoreDescription:
      'Reconstruction Error & Anomaly Score: Quantified as Mean Squared Error (MSE) between the input feature vector and its reconstructed output. This is NOT a probability; higher values indicate higher deviation from normal legitimate transaction behavior.',
    evaluationLimitations: [
      'Reconstruction error is an anomaly score, not a calibrated fraud probability; cannot be directly compared against probability scores.',
      'High noise transactions or unusual but legitimate spending behavior (e.g. rare overseas purchase) can produce false positive anomaly spikes.',
      'Threshold must be empirically derived from percentile distributions of reconstruction error on validation sets.',
    ],
    icon: Search,
  },
};

export function ModelFamilyPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const location = useLocation();
  const [models, setModels] = useState<ModelRegistryEntry[]>([]);
  const [loadedFamily, setLoadedFamily] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  let detected = familyId;
  if (!detected) {
    if (location.pathname.includes('xgboost')) detected = 'xgboost';
    else if (location.pathname.includes('mlp')) detected = 'mlp';
    else if (location.pathname.includes('autoencoder')) detected = 'autoencoder';
  }

  const key = (detected || 'xgboost').toLowerCase();
  const config = FAMILY_CONFIGS[key] || FAMILY_CONFIGS['xgboost'];
  const loading = loadedFamily !== config.family && error === null;

  useEffect(() => {
    let active = true;
    api
      .getModels()
      .then((res) => {
        if (active) {
          setModels(res.models.filter((m) => m.model_family.toLowerCase() === config.family.toLowerCase()));
          setLoadedFamily(config.family);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message);
        }
      });

    return () => {
      active = false;
    };
  }, [config.family]);

  const Icon = config.icon;

  return (
    <div className="page">
      <div className="mb-2">
        <Link to="/models" className="btn btn-sm">
          <ArrowLeft size={14} /> Back to Model Registry
        </Link>
      </div>

      {/* Model Family Header */}
      <header className="page-header">
        <div className="flex items-center gap-1 mb-1">
          <Icon size={24} color="var(--blue-600)" />
          <h1 style={{ marginBottom: 0 }}>{config.title}</h1>
        </div>
        <p>{config.subtitle}</p>
      </header>

      {/* Purpose & Core Concept */}
      <section className="mb-2">
        <p className="section-label">Architecture & Purpose</p>
        <div className="card">
          <div className="card-body">
            <p className="card-text mb-2">{config.purpose}</p>
            <div className="alert alert-info">
              <div>
                <strong>Score Interpretation: </strong>
                <span>{config.scoreDescription}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Evaluation Limitations */}
      <section className="mb-2">
        <p className="section-label">Evaluation Limitations & Operational Context</p>
        <div className="card">
          <div className="card-body">
            <ul style={{ paddingLeft: '1.25rem', color: 'var(--fg-700)', fontSize: '0.867rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {config.evaluationLimitations.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Models in this Family */}
      <section className="mb-2">
        <p className="section-label">Trained Deployments ({models.length})</p>
        {loading && <Loading message="Loading model metrics…" />}
        {error && <ErrorBox message={error} />}

        {!loading && !error && (
          <div className="grid-2">
            {models.map((m) => {
              const em = m.evaluation_metrics;
              const isAE = m.model_family === 'Autoencoder';

              return (
                <div key={m.model_id} className="card">
                  <div className="card-body">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="card-title" style={{ marginBottom: 0 }}>
                        {m.model_name}
                      </h3>
                      <span className={`badge ${m.is_available ? 'badge-green' : 'badge-gray'}`}>
                        {m.is_available ? 'Available' : 'Unavailable'}
                      </span>
                    </div>

                    <p className="text-xs text-muted mb-2">
                      Dataset: <strong>{DATASET_LABELS[m.dataset_id] ?? m.dataset_id}</strong> · Target: <code>{m.target_column}</code>
                    </p>

                    <div className="result-panel mb-2" style={{ padding: '0.75rem', fontSize: '0.8rem' }}>
                      <div className="result-row">
                        <span className="result-label">Model ID</span>
                        <span className="result-value">{m.model_id}</span>
                      </div>
                      <div className="result-row">
                        <span className="result-label">Score Type</span>
                        <span className="result-value">
                          {isAE ? 'Reconstruction Error (Anomaly Score)' : 'Fraud Probability'}
                        </span>
                      </div>
                      <div className="result-row">
                        <span className="result-label">Decision Threshold</span>
                        <span className="result-value">
                          {m.threshold != null ? m.threshold.toFixed(6) : 'N/A'}
                        </span>
                      </div>
                      <div className="result-row">
                        <span className="result-label">Model Artifact</span>
                        <span className="result-value">{m.model_artifact_filename}</span>
                      </div>
                      {m.scaler_artifact_filename && (
                        <div className="result-row">
                          <span className="result-label">Scaler Artifact</span>
                          <span className="result-value">{m.scaler_artifact_filename}</span>
                        </div>
                      )}
                    </div>

                    {/* Required Features */}
                    <div className="mb-2">
                      <p className="text-xs text-muted mb-1" style={{ fontWeight: 600 }}>Required Raw Features ({m.required_raw_features.length}):</p>
                      <div className="flex flex-wrap gap-1">
                        {m.required_raw_features.map((feat) => (
                          <span key={feat} className="badge badge-gray mono text-xs">
                            {feat}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Metrics Section (rendered only if actual API values exist) */}
                    {em && (
                      <div className="mb-2">
                        <p className="text-xs text-muted mb-1" style={{ fontWeight: 600 }}>Recorded Test Set Evaluation Metrics:</p>
                        <div className="grid-3 mb-1" style={{ gap: '0.5rem' }}>
                          {em.accuracy != null && (
                            <div className="card" style={{ padding: '0.5rem' }}>
                              <p className="text-xs text-muted">Accuracy</p>
                              <p className="text-sm mono" style={{ fontWeight: 700 }}>{(em.accuracy * 100).toFixed(2)}%</p>
                            </div>
                          )}
                          {em.precision != null && (
                            <div className="card" style={{ padding: '0.5rem' }}>
                              <p className="text-xs text-muted">Precision</p>
                              <p className="text-sm mono" style={{ fontWeight: 700 }}>{em.precision.toFixed(4)}</p>
                            </div>
                          )}
                          {em.recall != null && (
                            <div className="card" style={{ padding: '0.5rem' }}>
                              <p className="text-xs text-muted">Recall</p>
                              <p className="text-sm mono" style={{ fontWeight: 700 }}>{em.recall.toFixed(4)}</p>
                            </div>
                          )}
                          {em.f1_score != null && (
                            <div className="card" style={{ padding: '0.5rem' }}>
                              <p className="text-xs text-muted">F1 Score</p>
                              <p className="text-sm mono" style={{ fontWeight: 700 }}>{em.f1_score.toFixed(4)}</p>
                            </div>
                          )}
                          {em.roc_auc != null && (
                            <div className="card" style={{ padding: '0.5rem' }}>
                              <p className="text-xs text-muted">ROC-AUC</p>
                              <p className="text-sm mono" style={{ fontWeight: 700 }}>{em.roc_auc.toFixed(4)}</p>
                            </div>
                          )}
                          {em.pr_auc != null && (
                            <div className="card" style={{ padding: '0.5rem' }}>
                              <p className="text-xs text-muted">PR-AUC</p>
                              <p className="text-sm mono" style={{ fontWeight: 700 }}>{em.pr_auc.toFixed(4)}</p>
                            </div>
                          )}
                        </div>

                        {em.confusion_matrix && (
                          <div className="mt-1">
                            <p className="text-xs text-muted mb-1">Confusion Matrix:</p>
                            <div className="table-wrap" style={{ maxWidth: 280 }}>
                              <table className="table" style={{ fontSize: '0.75rem' }}>
                                <thead>
                                  <tr>
                                    <th></th>
                                    <th>Pred Legit</th>
                                    <th>Pred Fraud</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  <tr>
                                    <td style={{ fontWeight: 600 }}>Act Legit</td>
                                    <td className="table-mono">{em.confusion_matrix[0][0].toLocaleString()}</td>
                                    <td className="table-mono">{em.confusion_matrix[0][1].toLocaleString()}</td>
                                  </tr>
                                  <tr>
                                    <td style={{ fontWeight: 600 }}>Act Fraud</td>
                                    <td className="table-mono">{em.confusion_matrix[1][0].toLocaleString()}</td>
                                    <td className="table-mono">{em.confusion_matrix[1][1].toLocaleString()}</td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-1 mt-2">
                      <Link to={`/models/${m.model_id}`} className="btn btn-sm">
                        Inspect Details <ArrowRight size={14} />
                      </Link>
                      {m.is_available && (
                        <Link to={`/transaction?model=${m.model_id}&dataset=${m.dataset_id}`} className="btn btn-sm btn-primary">
                          Screen Transaction
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Model Family Switcher */}
      <section className="mt-3">
        <p className="section-label">Other Model Families</p>
        <div className="flex gap-1">
          {key !== 'xgboost' && (
            <Link to="/models/xgboost" className="btn btn-sm">
              XGBoost Classifier
            </Link>
          )}
          {key !== 'mlp' && (
            <Link to="/models/mlp" className="btn btn-sm">
              Multilayer Perceptron (MLP)
            </Link>
          )}
          {key !== 'autoencoder' && (
            <Link to="/models/autoencoder" className="btn btn-sm">
              Autoencoder Anomaly Detector
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}
