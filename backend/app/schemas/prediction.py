from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SinglePredictionRequest(BaseModel):
    """Payload for scoring a single financial transaction."""
    dataset_id: str = Field(..., description="Target dataset ID")
    model_id: str = Field(..., description="Target model ID")
    features: Dict[str, Any] = Field(..., description="Dictionary of raw feature values")


class SinglePredictionResponse(BaseModel):
    """Structured response for a single transaction fraud screening."""
    dataset_id: str
    model_id: str
    prediction_score: float = Field(..., description="Calculated fraud probability or anomaly error")
    score_type: str = Field(..., description="fraud_probability or mean_squared_reconstruction_error")
    threshold: float = Field(..., description="Decision threshold applied")
    risk_label: str = Field(..., description="Risk screening label: High Risk or Low Risk")
    explanation: str = Field(..., description="Human-readable decision explanation")
    preprocessed_vector: List[float] = Field(..., description="Preprocessed feature vector passed to model")


class CSVPredictionRow(BaseModel):
    """Single row outcome within a batch CSV screening."""
    row_index: int = Field(..., description="0-indexed original CSV row position")
    input_features: Dict[str, Any] = Field(..., description="Original input feature values")
    prediction_score: float
    score_type: str
    threshold: float
    risk_label: str
    decision_rule: str


class CSVPredictionResponse(BaseModel):
    """Structured response for batch CSV transaction screening."""
    dataset_id: str
    model_id: str
    total_rows: int
    high_risk_count: int
    low_risk_count: int
    threshold_used: float
    score_type: str
    predictions: List[CSVPredictionRow]


class SaveReportRequest(BaseModel):
    """Payload to explicitly persist a CSV screening report."""
    filename: str = Field(..., max_length=200, description="Target report filename")
    csv_content: str = Field(..., description="CSV report text to persist")
    summary: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata summary")


class ReportMetadataResponse(BaseModel):
    """Metadata of an explicitly saved report."""
    report_id: Optional[str] = None
    filename: str
    storage_path: str
    is_cloud: bool
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    size_bytes: Optional[int] = None
    summary: Optional[Dict[str, Any]] = None

