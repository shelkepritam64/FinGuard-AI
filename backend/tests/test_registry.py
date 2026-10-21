from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.registry import ModelRegistryService
from app.core.exceptions import ModelNotFoundError, ModelUnavailableError

client = TestClient(app)


def test_list_models():
    """Verify GET /api/models returns registered models with expected metadata."""
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "total_models" in data
    assert data["total_models"] >= 6
    
    model_ids = [m["model_id"] for m in data["models"]]
    # Primary 6 models
    assert "credit_1_xgboost" in model_ids
    assert "credit_1_mlp" in model_ids
    assert "credit_1_autoencoder" in model_ids
    assert "paysim_2_xgboost" in model_ids
    assert "paysim_2_mlp" in model_ids
    assert "paysim_2_autoencoder" in model_ids
    # Experimental / unavailable models
    assert "credit_1_lstm" in model_ids
    assert "paysim_2_lstm" in model_ids


def test_list_models_filter_dataset():
    """Verify filtering by dataset_id."""
    res_cc = client.get("/api/models?dataset_id=credit_card_dataset_1")
    assert res_cc.status_code == 200
    for m in res_cc.json()["models"]:
        assert m["dataset_id"] == "credit_card_dataset_1"

    res_ps = client.get("/api/models?dataset_id=paysim_dataset_2")
    assert res_ps.status_code == 200
    for m in res_ps.json()["models"]:
        assert m["dataset_id"] == "paysim_dataset_2"


def test_get_model_details():
    """Verify GET /api/models/{model_id} returns exact properties."""
    # Check Credit Card XGBoost
    res = client.get("/api/models/credit_1_xgboost")
    assert res.status_code == 200
    entry = res.json()
    assert entry["model_id"] == "credit_1_xgboost"
    assert entry["model_family"] == "XGBoost"
    assert entry["model_artifact_filename"] == "xgboost_model1_1.pkl"
    assert entry["score_type"] == "fraud_probability"
    assert entry["threshold"] == 0.47209590673446655
    assert entry["is_available"] is True
    assert entry["evaluation_metrics"] is not None
    assert "f1_score" in entry["evaluation_metrics"]

    # Check PaySim Autoencoder
    res_ae = client.get("/api/models/paysim_2_autoencoder")
    assert res_ae.status_code == 200
    entry_ae = res_ae.json()
    assert entry_ae["model_family"] == "Autoencoder"
    assert entry_ae["score_type"] == "mean_squared_reconstruction_error"
    assert entry_ae["threshold"] == 0.0790452710390086
    assert entry_ae["scaler_artifact_filename"] == "scaler_autoencoder_2.pkl"


def test_get_model_not_found():
    """Verify GET /api/models/{model_id} with unknown ID returns 404."""
    res = client.get("/api/models/non_existent_model_id")
    assert res.status_code == 404
    assert "not registered" in res.json()["detail"]


def test_model_availability_and_unavailable_reasons():
    """Verify unavailable models return explicit reasons."""
    res = client.get("/api/models/paysim_2_lstm")
    assert res.status_code == 200
    data = res.json()
    assert data["is_available"] is False
    assert data["status"] == "unavailable"
    assert "not trained" in data["unavailable_reason"].lower()

    res_cc_lstm = client.get("/api/models/credit_1_lstm")
    assert res_cc_lstm.status_code == 200
    data_cc = res_cc_lstm.json()
    assert data_cc["is_available"] is False
    assert "experimental" in data_cc["unavailable_reason"].lower()


def test_missing_artifacts_handling(tmp_path):
    """Verify registry marks models unavailable when files are absent."""
    empty_registry = ModelRegistryService(models_base_dir=tmp_path)
    model = empty_registry.get_model("credit_1_xgboost")
    assert model.is_available is False
    assert model.status == "unavailable"
    assert "not found on disk" in model.unavailable_reason


def test_get_metrics_endpoint():
    """Verify GET /api/metrics loads test metrics records."""
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_metrics"] >= 5
    first = data["records"][0]
    assert "model_id" in first
    assert "metrics" in first
    assert "accuracy" in first["metrics"]
