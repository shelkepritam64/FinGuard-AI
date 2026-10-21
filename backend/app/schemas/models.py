from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    """Recorded model evaluation metrics from original offline test evaluations."""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    decision_threshold: Optional[float] = None
    confusion_matrix: Optional[Any] = None
    extra: Optional[Dict[str, Any]] = None


class ModelRegistryEntry(BaseModel):
    """Centralized typed model registry entry."""
    model_id: str = Field(..., description="Unique model identifier")
    dataset_id: str = Field(..., description="Dataset identifier: credit_card_dataset_1 or paysim_dataset_2")
    model_name: str = Field(..., description="Human-readable model name")
    model_family: str = Field(..., description="Model family: XGBoost, MLP, Autoencoder, etc.")
    
    # Artifact metadata
    model_artifact_filename: str = Field(..., description="Exact model artifact filename on disk")
    scaler_artifact_filename: Optional[str] = Field(None, description="Scaler artifact filename if required")
    
    # Preprocessing & schema
    required_raw_features: List[str] = Field(..., description="Raw features expected from the user/CSV")
    ordered_model_features: List[str] = Field(..., description="Exact ordered feature vector passed to model")
    categorical_encoding_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="Encoding rules (e.g. one-hot mappings for categorical columns)"
    )
    
    # Decision semantics
    target_column: str = Field(..., description="Target column during training (e.g. fraud, isFraud)")
    threshold: Optional[float] = Field(None, description="Empirical decision threshold")
    score_type: str = Field(..., description="Score semantic: fraud_probability or mean_squared_reconstruction_error")
    prediction_rule: str = Field(..., description="Decision logic for High Risk flagging")
    
    # Status & Evaluation
    is_available: bool = Field(..., description="Whether model is verified and ready for inference")
    status: str = Field(..., description="Availability status: available, unavailable, experimental")
    unavailable_reason: Optional[str] = Field(None, description="Reason if model is unavailable")
    metrics_filename: Optional[str] = Field(None, description="Test metrics JSON filename")
    evaluation_metrics: Optional[EvaluationMetrics] = Field(None, description="Recorded evaluation test metrics")


class ModelListResponse(BaseModel):
    total_models: int
    models: List[ModelRegistryEntry]


class MetricsResponse(BaseModel):
    total_metrics: int
    records: List[Dict[str, Any]]
