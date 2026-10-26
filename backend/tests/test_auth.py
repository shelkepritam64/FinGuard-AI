"""
FinGuard AI — Authentication Test Suite
========================================
Tests: registration, duplicate email, invalid/weak passwords,
correct and incorrect login, expired tokens, unauthorized access,
suspended accounts, logout endpoint, and role enforcement.
"""

import uuid
import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.user_store import user_store
from app.core.auth import create_access_token
from app.core.rate_limiter import limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def manage_limiter_for_tests():
    """Disable global rate limiting for standard functional tests."""
    limiter.enabled = False
    yield
    limiter.enabled = True


# ───────────────── Registration ─────────────────

def test_user_registration_success():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "SecurePassword1",
        "full_name": "Test User"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "user"
    assert data["email"] == email
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user_id"]
    assert data["full_name"] == "Test User"


def test_user_registration_cannot_grant_admin_role():
    """Self-registration must never allow a caller to assign admin role."""
    email = f"hacker_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "SecurePassword1",
        "full_name": "Wannabe Admin",
        "role": "admin"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "user"


def test_registration_email_normalized():
    """Email should be lowercased and trimmed, rejecting duplicates case-insensitively."""
    email_raw = f"  CasedUser_{uuid.uuid4().hex[:8]}@Example.COM  "
    payload = {
        "email": email_raw,
        "password": "SecurePassword1",
        "full_name": "Cased User"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    assert res.json()["email"] == email_raw.strip().lower()


# ───────────────── Duplicate Email ─────────────────

def test_registration_duplicate_email_conflict():
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "SecurePassword1",
        "full_name": "First Instance"
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_registration_duplicate_email_case_insensitive():
    """Upper-case variant of an existing email must still be rejected as duplicate."""
    base = f"cidup_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": base,
        "password": "SecurePassword1",
        "full_name": "CI User"
    })
    res = client.post("/api/auth/register", json={
        "email": base.upper(),
        "password": "SecurePassword1",
        "full_name": "CI User 2"
    })
    assert res.status_code == 409


# ───────────────── Invalid / Weak Passwords ─────────────────

def test_registration_short_password_rejected():
    payload = {
        "email": f"short_{uuid.uuid4().hex[:8]}@example.com",
        "password": "short",
        "full_name": "Short Pass"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_registration_no_uppercase_rejected():
    payload = {
        "email": f"noup_{uuid.uuid4().hex[:8]}@example.com",
        "password": "lowercase1",
        "full_name": "No Upper"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert "uppercase" in response.json()["detail"].lower()


def test_registration_no_lowercase_rejected():
    payload = {
        "email": f"nolow_{uuid.uuid4().hex[:8]}@example.com",
        "password": "UPPERCASE1",
        "full_name": "No Lower"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert "lowercase" in response.json()["detail"].lower()


def test_registration_no_digit_rejected():
    payload = {
        "email": f"nodigit_{uuid.uuid4().hex[:8]}@example.com",
        "password": "NoDigitHere",
        "full_name": "No Digit"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert "digit" in response.json()["detail"].lower()


def test_registration_missing_email_rejected():
    response = client.post("/api/auth/register", json={
        "password": "SecurePassword1",
        "full_name": "No Email"
    })
    assert response.status_code == 422


def test_registration_invalid_email_format_rejected():
    response = client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "SecurePassword1",
        "full_name": "Bad Email"
    })
    assert response.status_code == 422


# ───────────────── Login: Correct Credentials ─────────────────

def test_login_success():
    email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": email,
        "password": "CorrectPassword1",
        "full_name": "Login Tester"
    })

    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "CorrectPassword1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "user"
    assert data["email"] == email
    assert data["full_name"] == "Login Tester"


def test_login_returns_valid_token_for_me():
    """Token returned by login must be usable for /auth/me immediately."""
    email = f"loginme_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": email,
        "password": "ValidPassword1",
        "full_name": "Token Tester"
    })
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "ValidPassword1"
    })
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


# ───────────────── Login: Incorrect Credentials ─────────────────

def test_login_wrong_password():
    email = f"wrongpw_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": email,
        "password": "CorrectPassword1",
        "full_name": "Wrong PW Tester"
    })

    bad_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword1"
    })
    assert bad_resp.status_code == 401
    assert "incorrect" in bad_resp.json()["detail"].lower()


def test_login_nonexistent_email():
    resp = client.post("/api/auth/login", json={
        "email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com",
        "password": "SomePassword1"
    })
    assert resp.status_code == 401
    # Generic message — does not reveal whether email exists
    assert "incorrect" in resp.json()["detail"].lower()


def test_login_error_does_not_reveal_user_existence():
    """The error for a wrong password vs nonexistent email must be identical."""
    email = f"reveal_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": email,
        "password": "CorrectPassword1",
        "full_name": "Reveal Test"
    })

    wrong_pw = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword1"
    })
    no_user = client.post("/api/auth/login", json={
        "email": f"ghost_{uuid.uuid4().hex[:8]}@example.com",
        "password": "WrongPassword1"
    })
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json()["detail"] == no_user.json()["detail"]


# ───────────────── Expired Token ─────────────────

def test_expired_token_rejected():
    token = create_access_token(
        {"sub": "expired-id", "email": "exp@example.com", "role": "user"},
        expires_delta=timedelta(seconds=-10)
    )
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


# ───────────────── Unauthorized Access ─────────────────

def test_me_requires_token():
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert "credentials" in resp.json()["detail"].lower() or "required" in resp.json()["detail"].lower()


def test_me_rejects_invalid_token():
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert resp.status_code == 401


def test_admin_endpoint_rejects_regular_user():
    """A valid user token must not grant access to admin-only endpoints."""
    email = f"nonadmin_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": "UserPassword1",
        "full_name": "Regular User"
    })
    token = reg.json()["access_token"]

    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert "denied" in resp.json()["detail"].lower() or "role" in resp.json()["detail"].lower()


def test_admin_endpoint_rejects_anonymous():
    resp = client.get("/api/admin/users")
    assert resp.status_code in (401, 403)


# ───────────────── Suspended Accounts ─────────────────

def test_suspended_user_login_rejected():
    email = f"suspended_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password12345A",
        "full_name": "Suspended Tester"
    })
    assert reg.status_code == 201
    user_id = reg.json()["user_id"]
    user_store.update_user(user_id, status="suspended")

    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password12345A"
    })
    assert login_resp.status_code == 403
    assert "suspended" in login_resp.json()["detail"].lower()


def test_suspended_user_me_rejected():
    email = f"suspme_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password12345A",
        "full_name": "Suspend ME"
    })
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]

    user_store.update_user(user_id, status="suspended")

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert "suspended" in resp.json()["detail"].lower()


# ───────────────── Logout Endpoint ─────────────────

def test_logout_endpoint():
    email = f"logout_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": "LogoutPassword1",
        "full_name": "Logout User"
    })
    token = reg.json()["access_token"]

    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged_out"


def test_logout_requires_auth():
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401


# ───────────────── Account Deletion ─────────────────

def test_delete_own_account():
    email = f"delete_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": "DeletePassword1",
        "full_name": "Delete Me"
    })
    token = reg.json()["access_token"]

    resp = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Token should no longer work (user doesn't exist)
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401


# ───────────────── Rate Limiting Triggers ─────────────────

def test_rate_limit_register_endpoint():
    """Trigger the 3/minute rate limit on registration and verify 429 response."""
    limiter.enabled = True
    try:
        # First 3 should succeed
        for _ in range(3):
            res = client.post("/api/auth/register", json={
                "email": f"rl_reg_{uuid.uuid4().hex[:8]}@example.com",
                "password": "ValidPassword1",
                "full_name": "RL Reg"
            })
            assert res.status_code == 201

        # 4th should be blocked by rate limiter
        blocked = client.post("/api/auth/register", json={
            "email": f"rl_reg_{uuid.uuid4().hex[:8]}@example.com",
            "password": "ValidPassword1",
            "full_name": "RL Reg"
        })
        assert blocked.status_code == 429
        assert "retry_after" in blocked.json() or "too many" in blocked.json().get("detail", "").lower()
    finally:
        limiter.enabled = False


def test_rate_limit_login_endpoint():
    """Trigger the 5/minute rate limit on login and verify 429 response."""
    limiter.enabled = True
    try:
        # First 5 attempts (invalid credentials) should return 401
        for _ in range(5):
            res = client.post("/api/auth/login", json={
                "email": f"rl_login_{uuid.uuid4().hex[:8]}@example.com",
                "password": "WrongPassword1"
            })
            assert res.status_code == 401

        # 6th attempt should be blocked with 429
        blocked = client.post("/api/auth/login", json={
            "email": "rl_login_excess@example.com",
            "password": "WrongPassword1"
        })
        assert blocked.status_code == 429
        assert "retry_after" in blocked.json() or "too many" in blocked.json().get("detail", "").lower()
    finally:
        limiter.enabled = False
