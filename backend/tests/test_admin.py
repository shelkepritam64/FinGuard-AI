import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import hash_password, create_access_token
from app.services.user_store import user_store

client = TestClient(app)


@pytest.fixture
def admin_token():
    email = "admin_fixture@finguard.ai"
    user = user_store.get_user_by_email(email)
    if not user:
        user = user_store.create_user(
            email=email,
            password_hash=hash_password("AdminPass123!"),
            full_name="Admin Fixture",
            role="admin",
            status="active"
        )
    return create_access_token({"sub": user["id"], "email": user["email"], "role": "admin"})


@pytest.fixture
def user_token():
    email = "standard_user_fixture@example.com"
    user = user_store.get_user_by_email(email)
    if not user:
        user = user_store.create_user(
            email=email,
            password_hash=hash_password("UserPass123!"),
            full_name="Standard User Fixture",
            role="user",
            status="active"
        )
    return create_access_token({"sub": user["id"], "email": user["email"], "role": "user"})


def test_regular_user_cannot_access_admin_endpoints(user_token):
    # Standard user attempting to list users
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]

    # Standard user attempting to view analytics
    resp = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403

    # Standard user attempting to view audit logs
    resp = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_admin():
    resp = client.get("/api/admin/users")
    assert resp.status_code == 401


def test_admin_can_list_and_search_users(admin_token):
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data
    assert isinstance(data["users"], list)


def test_admin_can_update_user_role_and_status(admin_token):
    # Create target user
    target_email = "target_mod@example.com"
    target = user_store.get_user_by_email(target_email)
    if not target:
        target = user_store.create_user(
            email=target_email,
            password_hash=hash_password("TargetPass123!"),
            full_name="Target Mod",
            role="user",
            status="active"
        )

    # Suspend user
    patch_resp = client.patch(
        f"/api/admin/users/{target['id']}",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "suspended"

    # Re-activate user and promote to admin
    patch_resp2 = client.patch(
        f"/api/admin/users/{target['id']}",
        json={"status": "active", "role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_resp2.status_code == 200
    assert patch_resp2.json()["status"] == "active"
    assert patch_resp2.json()["role"] == "admin"


def test_admin_cannot_demote_or_suspend_own_session(admin_token):
    # Find admin user ID
    user = user_store.get_user_by_email("admin_fixture@finguard.ai")
    assert user is not None

    resp = client.patch(
        f"/api/admin/users/{user['id']}",
        json={"role": "user"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    assert "cannot demote" in resp.json()["detail"].lower()

    resp_suspend = client.patch(
        f"/api/admin/users/{user['id']}",
        json={"status": "suspended"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_suspend.status_code == 400
    assert "cannot suspend" in resp_suspend.json()["detail"].lower()


def test_admin_analytics_and_audit_logs(admin_token):
    # Get analytics
    resp = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "by_model" in data
    assert "timeline" in data
    assert "active_users_7d" in data["summary"]
    assert "active_users_30d" in data["summary"]

    # Get audit logs
    audit_resp = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert isinstance(logs, list)


def test_normal_user_cannot_grant_themselves_admin_privileges(user_token):
    user = user_store.get_user_by_email("standard_user_fixture@example.com")
    assert user is not None

    # Standard user attempts to self-escalate role to admin via admin endpoint
    resp = client.patch(
        f"/api/admin/users/{user['id']}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]

    # Confirm in DB that the role remained strictly 'user'
    refreshed_user = user_store.get_user_by_id(user["id"])
    assert refreshed_user["role"] == "user"


def test_normal_user_cannot_create_or_delete_users(user_token):
    # Standard user attempts to create an admin account
    create_resp = client.post(
        "/api/admin/users",
        json={
            "email": "hacker_admin@example.com",
            "password": "HackerAdmin123!",
            "full_name": "Hacker Admin",
            "role": "admin",
            "status": "active"
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert create_resp.status_code == 403
    assert "Access denied" in create_resp.json()["detail"]

    # Standard user attempts to delete another user
    del_resp = client.delete(
        "/api/admin/users/some-target-id",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert del_resp.status_code == 403
    assert "Access denied" in del_resp.json()["detail"]


def test_admin_models_status_includes_metrics_and_counters(admin_token):
    resp = client.get("/api/admin/models-status", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_models" in data
    assert "models" in data
    assert "metrics_note" in data
    assert len(data["models"]) > 0
    first_model = data["models"][0]
    assert "threshold" in first_model
    assert "score_type" in first_model
    assert "total_predictions" in first_model

