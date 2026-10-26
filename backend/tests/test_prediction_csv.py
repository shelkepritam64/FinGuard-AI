import io
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_credit_card_csv_batch_prediction_json():
    """Verify batch CSV prediction returns structured JSON with preserved row indices."""
    csv_data = (
        "distance_from_home,distance_from_last_transaction,ratio_to_median_purchase_price,repeat_retailer,used_chip,used_pin_number,online_order\n"
        "10.5,0.2,1.1,1.0,1.0,0.0,0.0\n"
        "25.0,3.5,4.8,1.0,0.0,0.0,1.0\n"
        "500.0,50.0,15.0,0.0,0.0,0.0,1.0\n"
    )
    files = {"file": ("batch.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_xgboost"
    }

    response = client.post("/api/predict/csv", data=data, files=files)
    assert response.status_code == 200
    res = response.json()
    assert res["total_rows"] == 3
    assert len(res["predictions"]) == 3
    for i, row in enumerate(res["predictions"]):
        assert row["row_index"] == i
        assert "prediction_score" in row
        assert row["risk_label"] in ["High Risk", "Low Risk"]


def test_paysim_csv_batch_downloadable_csv():
    """Verify ?download=true returns downloadable CSV with Content-Disposition."""
    csv_data = (
        "step,amount,type\n"
        "1,150.0,PAYMENT\n"
        "2,50000.0,TRANSFER\n"
        "3,200.0,CASH_OUT\n"
    )
    files = {"file": ("transactions.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {
        "dataset_id": "paysim_dataset_2",
        "model_id": "paysim_2_mlp"
    }

    response = client.post("/api/predict/csv?download=true", data=data, files=files)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "paysim_2_mlp_predictions.csv" in response.headers["content-disposition"]

    # Read returned CSV
    df_out = pd.read_csv(io.BytesIO(response.content))
    assert len(df_out) == 3
    assert "row_index" in df_out.columns
    assert "prediction_score" in df_out.columns
    assert "risk_label" in df_out.columns
    assert "threshold" in df_out.columns
    assert "decision_rule" in df_out.columns
    assert list(df_out["row_index"]) == [0, 1, 2]


def test_csv_empty_file_rejected():
    """Verify empty CSV upload returns 400."""
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    data = {
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_xgboost"
    }
    response = client.post("/api/predict/csv", data=data, files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_csv_missing_columns_rejected():
    """Verify missing required columns returns 400."""
    csv_data = "distance_from_home,used_chip\n10.5,1.0\n"
    files = {"file": ("incomplete.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_xgboost"
    }
    response = client.post("/api/predict/csv", data=data, files=files)
    assert response.status_code == 400
    assert "Missing required input features" in response.json()["detail"]


def test_csv_nan_values_rejected():
    """Verify NaN values in features return 400."""
    csv_data = (
        "distance_from_home,distance_from_last_transaction,ratio_to_median_purchase_price,repeat_retailer,used_chip,used_pin_number,online_order\n"
        "10.5,,1.1,1.0,1.0,0.0,0.0\n"
    )
    files = {"file": ("nan.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_xgboost"
    }
    response = client.post("/api/predict/csv", data=data, files=files)
    assert response.status_code == 400
    assert "NaN or null" in response.json()["detail"]


def test_csv_target_columns_ignored():
    """Verify target column 'fraud' is ignored in batch processing."""
    csv_data = (
        "distance_from_home,distance_from_last_transaction,ratio_to_median_purchase_price,repeat_retailer,used_chip,used_pin_number,online_order,fraud\n"
        "10.5,0.2,1.1,1.0,1.0,0.0,0.0,0\n"
        "25.0,3.5,4.8,1.0,0.0,0.0,1.0,1\n"
    )
    files = {"file": ("with_fraud.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    data = {
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_xgboost"
    }
    response = client.post("/api/predict/csv", data=data, files=files)
    assert response.status_code == 200
    assert response.json()["total_rows"] == 2


def test_csv_binary_file_rejected():
    """Verify binary content disguised as CSV is rejected."""
    binary_data = b"\x00\x01\x02\xFF\xFE\x00\x00PNG\x00\x00\x00"
    files = {"file": ("malicious.csv", io.BytesIO(binary_data), "text/csv")}
    data = {
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_xgboost"
    }
    response = client.post("/api/predict/csv", data=data, files=files)
    assert response.status_code == 400
    assert "binary data" in response.json()["detail"].lower() or "utf-8" in response.json()["detail"].lower()


def test_csv_oversized_file_rejected():
    """Verify uploads exceeding max allowed size are rejected."""
    # Create fake oversized content (> 10MB)
    fake_chunk = b"distance_from_home,used_chip\n" + b"1.0,1.0\n" * 1000
    oversized_data = b"0" * (11 * 1024 * 1024)
    files = {"file": ("huge.csv", io.BytesIO(oversized_data), "text/csv")}
    data = {
        "dataset_id": "credit_card_dataset_1",
        "model_id": "credit_1_xgboost"
    }
    response = client.post("/api/predict/csv", data=data, files=files)
    assert response.status_code == 400
    assert "exceeds maximum upload size" in response.json()["detail"]

