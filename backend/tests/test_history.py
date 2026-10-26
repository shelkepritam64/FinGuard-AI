import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import hash_password, create_access_token
from app.services.user_store import UserStore, user_store

client = TestClient(app)


@pytest.fixture
def user_a():
    email = "user_a_hist@example.com"
    user = user_store.get_user_by_email(email)
    if not user:
        user = user_store.create_user(
            email=email,
            password_hash=hash_password("PassUserA123!"),
            full_name="User Alpha",
            role="user",
            status="active"
        )
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    return {"user": user, "token": token}


@pytest.fixture
def user_b():
    email = "user_b_hist@example.com"
    user = user_store.get_user_by_email(email)
    if not user:
        user = user_store.create_user(
            email=email,
            password_hash=hash_password("PassUserB123!"),
            full_name="User Beta",
            role="user",
            status="active"
        )
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    return {"user": user, "token": token}


def test_user_cannot_access_another_user_history(user_a, user_b):
    # Clear any previous test history for both
    user_store.clear_user_history(user_a["user"]["id"])
    user_store.clear_user_history(user_b["user"]["id"])

    # User A performs a single transaction screening
    sample_features = {
        "distance_from_home": 10.5,
        "distance_from_last_transaction": 2.1,
        "ratio_to_median_purchase_price": 1.2,
        "repeat_retailer": 1,
        "used_chip": 1,
        "used_pin_number": 1,
        "online_order": 0
    }
    pred_resp = client.post(
        "/api/predict/single",
        headers={"Authorization": f"Bearer {user_a['token']}"},
        json={
            "dataset_id": "credit_card_dataset_1",
            "model_id": "credit_1_xgboost",
            "features": sample_features
        }
    )
    assert pred_resp.status_code == 200

    # User A fetches their history
    resp_a = client.get(
        "/api/auth/history",
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total"] == 1
    assert len(data_a["items"]) == 1
    assert data_a["items"][0]["model_id"] == "credit_1_xgboost"
    assert data_a["items"][0]["user_id"] == user_a["user"]["id"]

    # User B fetches their history -> MUST be empty (0 items)
    resp_b = client.get(
        "/api/auth/history",
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["total"] == 0
    assert len(data_b["items"]) == 0

    # User B maliciously supplies user_id of User A in query params
    # Rule 4: Server MUST NEVER trust client-supplied user_id to determine ownership!
    resp_malicious = client.get(
        f"/api/auth/history?user_id={user_a['user']['id']}",
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert resp_malicious.status_code == 200
    data_malicious = resp_malicious.json()
    # Still returns 0 because server verified identity (sub from User B's token) is used!
    assert data_malicious["total"] == 0
    assert len(data_malicious["items"]) == 0


def test_unauthenticated_cannot_access_history():
    resp = client.get("/api/auth/history")
    assert resp.status_code == 401


def test_history_zero_raw_transaction_payload(user_a):
    user_store.clear_user_history(user_a["user"]["id"])

    user_store.record_screening_history(
        user_id=user_a["user"]["id"],
        screening_type="single_screening",
        dataset_id="credit_card_dataset_1",
        model_id="credit_1_xgboost",
        score_type="fraud_probability",
        prediction_score=0.885,
        threshold=0.5,
        risk_classification="High Risk",
        request_status="completed",
        row_count=1,
        flagged_count=1
    )

    resp = client.get(
        "/api/auth/history",
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]

    # Verify expected metadata is present
    assert item["model_id"] == "credit_1_xgboost"
    assert item["dataset_id"] == "credit_card_dataset_1"
    assert item["score_type"] == "fraud_probability"
    assert item["risk_classification"] == "High Risk"
    assert item["request_status"] == "completed"
    assert item["prediction_score"] == 0.885
    assert item["threshold"] == 0.5
    assert "timestamp" in item

    # Verify NO raw feature inputs or transaction payloads exist in the object
    assert "features" not in item
    assert "input_features" not in item
    assert "raw_data" not in item
    assert "csv_content" not in item


def test_history_search_and_filtering(user_a):
    user_store.clear_user_history(user_a["user"]["id"])

    # Create 3 distinct records
    user_store.record_screening_history(
        user_id=user_a["user"]["id"],
        screening_type="single_screening",
        dataset_id="credit_card_dataset_1",
        model_id="credit_1_xgboost",
        risk_classification="High Risk"
    )
    user_store.record_screening_history(
        user_id=user_a["user"]["id"],
        screening_type="single_screening",
        dataset_id="paysim_dataset_2",
        model_id="paysim_1_xgboost",
        risk_classification="Low Risk"
    )
    user_store.record_screening_history(
        user_id=user_a["user"]["id"],
        screening_type="csv_batch",
        dataset_id="credit_card_dataset_1",
        model_id="credit_1_mlp",
        risk_classification="High Risk",
        row_count=150,
        flagged_count=5
    )

    headers = {"Authorization": f"Bearer {user_a['token']}"}

    # 1. Total
    r_all = client.get("/api/auth/history", headers=headers).json()
    assert r_all["total"] == 3

    # 2. Filter by screening_type
    r_csv = client.get("/api/auth/history?screening_type=csv_batch", headers=headers).json()
    assert r_csv["total"] == 1
    assert r_csv["items"][0]["model_id"] == "credit_1_mlp"

    # 3. Filter by risk_classification
    r_high = client.get("/api/auth/history?risk_classification=High Risk", headers=headers).json()
    assert r_high["total"] == 2

    # 4. Search query
    r_search = client.get("/api/auth/history?search=paysim", headers=headers).json()
    assert r_search["total"] == 1
    assert r_search["items"][0]["dataset_id"] == "paysim_dataset_2"

    # 5. Pagination
    r_page = client.get("/api/auth/history?limit=1&offset=0", headers=headers).json()
    assert len(r_page["items"]) == 1
    assert r_page["total"] == 3


def test_history_persists_across_restarts(tmp_path):
    """Verify that records persist in SQLite (not held only in an in-memory dict)."""
    db_file = tmp_path / "persistent_history_test.db"

    # Instance 1
    store1 = UserStore(db_path=db_file)
    test_user_id = "test-persist-uid"
    store1.record_screening_history(
        user_id=test_user_id,
        screening_type="single_screening",
        dataset_id="credit_card_dataset_1",
        model_id="credit_1_autoencoder",
        risk_classification="Low Risk"
    )

    # Simulate backend restart with a completely new UserStore instance reading the same file
    store2 = UserStore(db_path=db_file)
    rows, total = store2.get_user_screening_history(user_id=test_user_id)
    assert total == 1
    assert rows[0]["model_id"] == "credit_1_autoencoder"
    assert rows[0]["risk_classification"] == "Low Risk"


def test_account_deletion_purges_screening_history(tmp_path):
    db_file = tmp_path / "delete_purge_test.db"
    store = UserStore(db_path=db_file)
    user = store.create_user(
        email="purge_me@example.com",
        password_hash="[HASH]",
        full_name="Purge Me",
        role="user"
    )
    store.record_screening_history(
        user_id=user["id"],
        screening_type="single_screening",
        dataset_id="paysim_dataset_2",
        model_id="paysim_2_mlp",
        risk_classification="High Risk"
    )

    # Verify history exists
    _, total = store.get_user_screening_history(user["id"])
    assert total == 1

    # Delete user
    store.delete_user(user["id"])

    # Verify history is purged
    _, total_after = store.get_user_screening_history(user["id"])
    assert total_after == 0
