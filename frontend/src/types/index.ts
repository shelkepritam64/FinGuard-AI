/**
 * FinGuard AI — Core Domain Types
 * Matches the FastAPI backend Pydantic schemas exactly.
 */

/* ── Dataset & Model Enumerations ── */

export type DatasetId = 'credit_card_dataset_1' | 'paysim_dataset_2';
export type ModelFamily = 'XGBoost' | 'MLP' | 'Autoencoder' | 'LSTM';
export type ScoreType = 'fraud_probability' | 'mean_squared_reconstruction_error';
export type RiskLabel = 'High Risk' | 'Low Risk';

/* ── Health ── */

export interface HealthStatus {
  status: string;
  app: string;
  environment: string;
  models_dir_configured: string;
  models_dir_exists: boolean;
  datasets_dir_configured: string;
  datasets_dir_exists: boolean;
}

/* ── Evaluation Metrics ── */

export interface EvaluationMetrics {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  roc_auc: number | null;
  pr_auc: number | null;
  decision_threshold: number | null;
  confusion_matrix: number[][] | null;
  extra: Record<string, unknown> | null;
}

/* ── Model Registry ── */

export interface ModelRegistryEntry {
  model_id: string;
  dataset_id: DatasetId;
  model_name: string;
  model_family: ModelFamily;
  model_artifact_filename: string;
  scaler_artifact_filename: string | null;
  required_raw_features: string[];
  ordered_model_features: string[];
  categorical_encoding_rules: Record<string, unknown>;
  target_column: string;
  threshold: number | null;
  score_type: ScoreType;
  prediction_rule: string;
  is_available: boolean;
  status: string;
  unavailable_reason: string | null;
  metrics_filename: string | null;
  evaluation_metrics: EvaluationMetrics | null;
}

export interface ModelListResponse {
  total_models: number;
  models: ModelRegistryEntry[];
}

/* ── Metrics ── */

export interface MetricsRecord {
  model_id: string;
  model_name: string;
  dataset_id: string;
  model_family: string;
  metrics_file: string;
  metrics: EvaluationMetrics;
}

export interface MetricsResponse {
  total_metrics: number;
  records: MetricsRecord[];
}

/* ── Single Prediction ── */

export interface SinglePredictionRequest {
  dataset_id: string;
  model_id: string;
  features: Record<string, number | string>;
}

export interface SinglePredictionResponse {
  dataset_id: string;
  model_id: string;
  prediction_score: number;
  score_type: ScoreType;
  threshold: number;
  risk_label: RiskLabel;
  explanation: string;
  preprocessed_vector: number[];
}

/* ── CSV Prediction ── */

export interface CSVPredictionRow {
  row_index: number;
  input_features: Record<string, unknown>;
  prediction_score: number;
  score_type: ScoreType;
  threshold: number;
  risk_label: RiskLabel;
  decision_rule: string;
}

export interface CSVPredictionResponse {
  dataset_id: string;
  model_id: string;
  total_rows: number;
  high_risk_count: number;
  low_risk_count: number;
  threshold_used: number;
  score_type: ScoreType;
  predictions: CSVPredictionRow[];
}

/* ── Helpers ── */

export const DATASET_LABELS: Record<DatasetId, string> = {
  credit_card_dataset_1: 'Credit Card Fraud Detection',
  paysim_dataset_2: 'PaySim Synthetic Mobile Money',
};

export const MODEL_FAMILY_LABELS: Record<ModelFamily, string> = {
  XGBoost: 'XGBoost Gradient Boosted Trees',
  MLP: 'Multilayer Perceptron (MLP)',
  Autoencoder: 'Autoencoder Anomaly Detection',
  LSTM: 'LSTM Sequence Model',
};
