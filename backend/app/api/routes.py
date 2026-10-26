import io
from pathlib import Path
from typing import Optional, List
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from fastapi.responses import StreamingResponse

from app.config import settings
from app.services.registry import registry_service
from app.services.preprocessor import validate_and_preprocess_single, preprocess_dataframe
from app.services.engine import inference_engine
from app.services.user_store import user_store
from app.services.storage import storage_service
from app.core.auth import get_optional_current_user, get_current_user
from app.schemas.models import ModelListResponse, ModelRegistryEntry, MetricsResponse
from app.schemas.prediction import (
    SinglePredictionRequest,
    SinglePredictionResponse,
    CSVPredictionResponse,
    CSVPredictionRow,
    SaveReportRequest,
    ReportMetadataResponse
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
def predict_single(
    payload: SinglePredictionRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
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

    # Privacy-conscious usage metrics (anonymized metadata only, zero feature payloads stored)
    user_id = current_user["id"] if current_user else "anonymous"
    if current_user:
        user_store.increment_user_usage(current_user["id"], screening_increment=1)
        user_store.record_screening_history(
            user_id=current_user["id"],
            screening_type="single_screening",
            dataset_id=model_entry.dataset_id,
            model_id=model_entry.model_id,
            score_type=model_entry.score_type,
            prediction_score=float(scores[0]),
            threshold=float(thresholds[0]),
            risk_classification=str(risk_labels[0]),
            request_status="completed",
            row_count=1,
            flagged_count=(1 if str(risk_labels[0]) == "High Risk" else 0)
        )
    user_store.record_usage_event(
        user_id=user_id,
        event_type="single_screening",
        dataset_id=model_entry.dataset_id,
        model_id=model_entry.model_id,
        row_count=1,
        flagged_count=(1 if str(risk_labels[0]) == "High Risk" else 0)
    )

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
    download: bool = Query(False, description="If true, returns a downloadable CSV attachment"),
    current_user: Optional[dict] = Depends(get_optional_current_user)
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
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

        if len(contents) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # Content validation: Must be UTF-8/ASCII text without null bytes
        try:
            sample_chunk = contents[:4096].decode("utf-8-sig")
            if "\x00" in sample_chunk:
                raise HTTPException(status_code=400, detail="Uploaded file contains binary data and is not a valid text CSV.")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 encoded text CSV.")

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

        # Calculate aggregate counts
        high_risk_count = sum(1 for label in risk_labels if str(label) == "High Risk")
        low_risk_count = len(risk_labels) - high_risk_count

        # Privacy-conscious usage metrics (only aggregated counts, zero transaction payloads stored)
        user_id = current_user["id"] if current_user else "anonymous"
        if current_user:
            user_store.increment_user_usage(current_user["id"], csv_increment=1)
            user_store.record_screening_history(
                user_id=current_user["id"],
                screening_type="csv_batch",
                dataset_id=model_entry.dataset_id,
                model_id=model_entry.model_id,
                score_type=model_entry.score_type,
                prediction_score=None,
                threshold=float(model_entry.threshold),
                risk_classification=("High Risk" if high_risk_count > 0 else "Low Risk"),
                request_status="completed",
                row_count=len(df_input),
                flagged_count=high_risk_count
            )
        user_store.record_usage_event(
            user_id=user_id,
            event_type="csv_batch",
            dataset_id=model_entry.dataset_id,
            model_id=model_entry.model_id,
            row_count=len(df_input),
            flagged_count=high_risk_count
        )

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
    finally:
        # Guarantee closure and cleanup of uploaded temporary file resources
        await file.close()


# ── Explicit Saved Reports (Opt-in persistence with strict ownership validation) ──

@api_router.post("/reports/save", response_model=ReportMetadataResponse, tags=["Reports"])
def save_user_report(
    payload: SaveReportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Explicitly persist a CSV prediction screening report.
    Strictly restricted to authenticated user namespace with zero leakage.
    """
    if not payload.csv_content.strip():
        raise HTTPException(status_code=400, detail="Report CSV content cannot be empty.")

    # Sanitize filename
    clean_filename = Path(payload.filename).name.replace(" ", "_")
    if not clean_filename.lower().endswith(".csv"):
        clean_filename = f"{clean_filename}.csv"

    try:
        report_meta = storage_service.save_report(
            user_id=current_user["id"],
            filename=clean_filename,
            csv_content=payload.csv_content,
            summary=payload.summary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist report: {str(e)}")

    return ReportMetadataResponse(
        report_id=report_meta["report_id"],
        filename=report_meta["filename"],
        storage_path=report_meta["storage_path"],
        is_cloud=report_meta["is_cloud"],
        created_at=report_meta["created_at"],
        size_bytes=len(payload.csv_content.encode("utf-8")),
        summary=payload.summary
    )


@api_router.get("/reports", response_model=List[ReportMetadataResponse], tags=["Reports"])
def list_user_reports(current_user: dict = Depends(get_current_user)):
    """List saved reports owned by the authenticated user."""
    reports = storage_service.list_reports(user_id=current_user["id"])
    return [
        ReportMetadataResponse(
            filename=r["filename"],
            storage_path=r["storage_path"],
            is_cloud=r["is_cloud"],
            size_bytes=r.get("size_bytes"),
            last_modified=r.get("last_modified")
        )
        for r in reports
    ]


@api_router.get("/reports/download", tags=["Reports"])
def download_user_report(
    key: str = Query(..., description="Report storage key"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate secure download for an explicitly saved report.
    Verifies ownership: report key must begin with reports/{user_id}/.
    """
    expected_prefix = f"reports/{current_user['id']}/"
    if not key.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Access denied: You do not own this storage object.")

    try:
        if storage_service.is_aws:
            url = storage_service.generate_download_url(user_id=current_user["id"], report_key=key)
            return {"download_url": url, "expires_in": 3600}
        else:
            content = storage_service.get_report_content(user_id=current_user["id"], report_key=key)
            filename = Path(key).name
            return StreamingResponse(
                io.BytesIO(content.encode("utf-8")),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/reports", tags=["Reports"])
def delete_user_report(
    key: str = Query(..., description="Report storage key to delete"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an explicitly saved report.
    Verifies user ownership before deleting.
    """
    try:
        success = storage_service.delete_report(user_id=current_user["id"], report_key=key)
        if not success:
            raise HTTPException(status_code=404, detail="Report not found or already deleted.")
        return {"status": "deleted", "storage_path": key}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

