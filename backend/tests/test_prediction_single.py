import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Small synthetic fixtures for testing
CREDIT_CARD_SAMPLE = {
    "distance_from_home": 57.8778,
    "distance_from_last_transaction": 0.3111,
    "ratio_to_median_purchase_price": 1.9459,
    "repeat_retailer": 1.0,
    "used_chip": 1.0,
    "used_pin_number": 0.0,
    "online_order": 0.0
}

PAYSIM_SAMPLE = {
    "step": 1,
    "amount": 9839.64,
    "type": "PAYMENT"
}


@pytest.mark.parametrize("model_id", [
    "credit_1_xgboost",
    "credit_1_mlp",
    "credit_1_autoencoder"
])
def test_credit_card_single_prediction_models(model_id):
    """Test single transaction prediction on all verified Credit Card models."""
    response = client.post("/api/predict/single", json={
        "dataset_id": "credit_card_dataset_1",
        "model_id": model_id,
        "features": CREDIT_CARD_SAMPLE
    })
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "credit_card_dataset_1"
    assert data["model_id"] == model_id
    assert isinstance(data["prediction_score"], float)
    assert data["risk_label"] in ["High Risk", "Low Risk"]
    assert len(data["preprocessed_vector"]) == 7

    if "autoencoder" in model_id:
        assert data["score_type"] == "mean_squared_reconstruction_error"
        assert "reconstruction anomaly error" in data["explanation"].lower()
    else:
        assert data["score_type"] == "fraud_probability"
        assert "predicted fraud probability" in data["explanation"].lower()


@pytest.mark.parametrize("model_id", [
    "paysim_2_xgboost",
    "paysim_2_mlp",
    "paysim_2_autoencoder"
])
def test_paysim_single_prediction_models(model_id):
    """Test single transaction prediction on all verified PaySim models."""
    response = client.post("/api/predict/single", json={
        "dataset_id": "paysim_dataset_2",
        "model_id": model_id,
        "features": PAYSIM_SAMPLE
    })
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "paysim_dataset_2"
    assert data["model_id"] == model_id
    assert isinstance(data["prediction_score"], float)
    assert data["risk_label"] in ["High Risk", "Low Risk"]
    assert len(data["preprocessed_vector"]) == 7


def test_unavailable_model_prediction_rejected():
    """Verify inference on unavailable model returns 400 with explanation."""
    response = client.post("/api/predict/single", json={
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_lstm",
        "features": CREDIT_CARD_SAMPLE
    })
    assert response.status_code == 400
    assert "unavailable" in response.json()["detail"].lower()


def test_dataset_mismatch_rejected():
    """Verify requesting Credit Card data for PaySim model returns 400."""
    response = client.post("/api/predict/single", json={
        "dataset_id": "paysim_dataset_2",
        "model_id": "credit_1_xgboost",
        "features": PAYSIM_SAMPLE
    })
    assert response.status_code == 400
    assert "Dataset mismatch" in response.json()["detail"]


def test_nonexistent_model_rejected():
    """Verify unknown model ID returns 404."""
    response = client.post("/api/predict/single", json={
        "dataset_id": "credit_card_dataset_1",
        "model_id": "unknown_model_xyz",
        "features": CREDIT_CARD_SAMPLE
    })
    assert response.status_code == 404


def test_threshold_behavior_and_risk_label():
    """Verify that score >= threshold yields High Risk, else Low Risk."""
    # Test high anomaly simulation on credit card autoencoder
    extreme_outlier = {
        "distance_from_home": 99999.0,
        "distance_from_last_transaction": 8888.0,
        "ratio_to_median_purchase_price": 500.0,
        "repeat_retailer": 0.0,
        "used_chip": 0.0,
        "used_pin_number": 0.0,
        "online_order": 1.0
    }
    response = client.post("/api/predict/single", json={
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_autoencoder",
        "features": extreme_outlier
    })
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_score"] >= data["threshold"]
    assert data["risk_label"] == "High Risk"
