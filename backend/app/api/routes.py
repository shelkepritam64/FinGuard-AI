import io
import pandas as pd
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse

from app.config import settings
from app.services.registry import registry_service
from app.services.preprocessor import validate_and_preprocess_single, preprocess_dataframe
from app.services.engine import inference_engine
from app.schemas.models import ModelListResponse, ModelRegistryEntry, MetricsResponse
from app.schemas.prediction import (
    SinglePredictionRequest,
    SinglePredictionResponse,
    CSVPredictionResponse,
    CSVPredictionRow
)
from app.core.exceptions import (
    ModelNotFoundError,
    ModelUnavailableError,
    PreprocessingError,
    ArtifactMissingError,
    InferenceError
)

api_router = APIRouter()


@api_router.get("/health", tags=["System"])
def health_check():
    """System health check and path configuration validation."""
    models_dir = settings.resolved_models_dir
    datasets_dir = settings.resolved_datasets_dir

    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "models_dir_configured": str(models_dir),
        "models_dir_exists": models_dir.exists(),
        "datasets_dir_configured": str(datasets_dir),
        "datasets_dir_exists": datasets_dir.exists()
    }


@api_router.get("/models", response_model=ModelListResponse, tags=["Models"])
def list_models(dataset_id: Optional[str] = Query(None, description="Filter models by dataset ID")):
    """List all registered model families, configurations, and verification status."""
    models = registry_service.list_models(dataset_id=dataset_id)
    return ModelListResponse(total_models=len(models), models=models)


@api_router.get("/models/{model_id}", response_model=ModelRegistryEntry, tags=["Models"])
def get_model(model_id: str):
    """Get metadata, feature schema, decision threshold, and metrics for a specific model ID."""
    try:
        return registry_service.get_model(model_id)
    except ModelNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@api_router.get("/metrics", response_model=MetricsResponse, tags=["Metrics"])
def get_metrics():
    """Return recorded test evaluation metrics read dynamically from model artifact files."""
    metrics_list = registry_service.get_all_metrics()
    return MetricsResponse(total_metrics=len(metrics_list), records=metrics_list)


@api_router.post("/predict/single", response_model=SinglePredictionResponse, tags=["Prediction"])
def predict_single(payload: SinglePredictionRequest):
    """
    Score a single financial transaction against a verified model.
    Applies exact training preprocessing and returns risk screening result.
    """
    try:
        model_entry = registry_service.get_verified_model(payload.model_id)
    except ModelNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ModelUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate dataset alignment
    if payload.dataset_id != model_entry.dataset_id:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset mismatch: Model '{payload.model_id}' belongs to dataset '{model_entry.dataset_id}', not '{payload.dataset_id}'."
        )

    # Preprocessing
    try:
        X_matrix, vector_list = validate_and_preprocess_single(model_entry, payload.features)
    except PreprocessingError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Inference
    try:
        scores, thresholds, risk_labels, explanations = inference_engine.predict(model_entry, X_matrix)
    except ArtifactMissingError as e:
        raise HTTPException(status_code=500, detail=f"Model artifact unavailable: {str(e)}")
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=f"Inference execution failed: {str(e)}")

    return SinglePredictionResponse(
        dataset_id=model_entry.dataset_id,
        model_id=model_entry.model_id,
        prediction_score=float(scores[0]),
        score_type=model_entry.score_type,
        threshold=float(thresholds[0]),
        risk_label=str(risk_labels[0]),
        explanation=str(explanations[0]),
        preprocessed_vector=vector_list
    )


@api_router.post("/predict/csv", tags=["Prediction"])
async def predict_csv(
    dataset_id: str = Form(..., description="Target dataset ID"),
    model_id: str = Form(..., description="Target model ID"),
    file: UploadFile = File(..., description="CSV file of transactions"),
    format: str = Query("json", description="Output format: 'json' or 'csv'"),
    download: bool = Query(False, description="If true, returns a downloadable CSV attachment")
):
    """
    Batch transaction screening from uploaded CSV.
    Validates structure, reproduces training pipeline, and returns predictions with original data.
    """
    try:
        model_entry = registry_service.get_verified_model(model_id)
    except ModelNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ModelUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if dataset_id != model_entry.dataset_id:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset mismatch: Model '{model_id}' belongs to dataset '{model_entry.dataset_id}', not '{dataset_id}'."
        )

    # Read and validate file content
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    try:
        df_input = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed CSV file could not be parsed: {str(e)}")

    if df_input.empty:
        raise HTTPException(status_code=400, detail="CSV contains no data rows.")

    # Preprocessing
    try:
        X_matrix = preprocess_dataframe(model_entry, df_input)
    except PreprocessingError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Inference
    try:
        scores, thresholds, risk_labels, explanations = inference_engine.predict(model_entry, X_matrix)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch inference failed: {str(e)}")

    # Construct results
    if download or format.lower() == "csv":
        out_df = df_input.copy()
        out_df.insert(0, "row_index", range(len(out_df)))
        out_df["prediction_score"] = scores
        out_df["score_type"] = model_entry.score_type
        out_df["threshold"] = thresholds
        out_df["risk_label"] = risk_labels
        out_df["decision_rule"] = explanations

        csv_buffer = io.StringIO()
        out_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        filename = f"{model_id}_predictions.csv"
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    # JSON response
    prediction_rows = []
    high_risk_count = 0
    low_risk_count = 0

    for i in range(len(df_input)):
        label = str(risk_labels[i])
        if label == "High Risk":
            high_risk_count += 1
        else:
            low_risk_count += 1

        row_dict = df_input.iloc[i].to_dict()
        # Clean any float NaN if present for JSON serialization
        clean_row_dict = {
            k: (None if pd.isna(v) else v) for k, v in row_dict.items()
        }

        prediction_rows.append(CSVPredictionRow(
            row_index=i,
            input_features=clean_row_dict,
            prediction_score=float(scores[i]),
            score_type=model_entry.score_type,
            threshold=float(thresholds[i]),
            risk_label=label,
            decision_rule=str(explanations[i])
        ))

    return CSVPredictionResponse(
        dataset_id=model_entry.dataset_id,
        model_id=model_entry.model_id,
        total_rows=len(df_input),
        high_risk_count=high_risk_count,
        low_risk_count=low_risk_count,
        threshold_used=float(model_entry.threshold),
        score_type=model_entry.score_type,
        predictions=prediction_rows
    )
