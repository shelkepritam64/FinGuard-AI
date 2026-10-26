import pytest
import uuid
from app.services.user_store import UserStore, user_store
from app.core.auth import verify_password
from scripts.seed_admin import validate_password_strength, bootstrap_admin


@pytest.fixture
def temp_user_store(tmp_path):
    """Provide an isolated, clean SQLite user store for bootstrap tests."""
    db_file = tmp_path / "test_seed_admin.db"
    store = UserStore(db_path=db_file)
    return store


# ── Password Validation Tests ──

def test_password_validation_too_short():
    valid, issues = validate_password_strength("Short1A")
    assert not valid
    assert any("at least 8 characters" in msg for msg in issues)


def test_password_validation_missing_uppercase_user_considered_demo_password():
    """
    Test the user's requested demo password 'admin@123'.
    Must explicitly fail because it lacks an uppercase letter.
    """
    valid, issues = validate_password_strength("admin@123")
    assert not valid
    assert any("uppercase letter" in msg for msg in issues)


def test_password_validation_missing_lowercase():
    valid, issues = validate_password_strength("ADMIN@123")
    assert not valid
    assert any("lowercase letter" in msg for msg in issues)


def test_password_validation_missing_digit():
    valid, issues = validate_password_strength("AdminPassword!")
    assert not valid
    assert any("numeric digit" in msg for msg in issues)


def test_password_validation_valid():
    valid, issues = validate_password_strength("FinGuardAdmin123!")
    assert valid
    assert len(issues) == 0


# ── Account Creation & Role Assignment Tests ──

def test_bootstrap_initial_admin_creation(temp_user_store):
    email = "admin123@gmail.com"
    password = "AdminSecurePass123!"

    success, msg, user = bootstrap_admin(
        email=email,
        password=password,
        full_name="Lead Admin",
        store=temp_user_store
    )

    assert success
    assert user is not None
    assert user["email"] == email
    assert user["role"] == "admin"
    assert user["status"] == "active"
    assert user["full_name"] == "Lead Admin"

    # Verify password hash is stored safely (not plaintext)
    assert user["password_hash"] != password
    assert verify_password(password, user["password_hash"])

    # Verify audit log was recorded without credentials
    logs = temp_user_store.get_audit_logs()
    assert len(logs) == 1
    log = logs[0]
    assert log["actor_email"] == "system:bootstrap"
    assert log["action"] == "seed_initial_admin"
    assert log["target_email"] == email
    assert password not in log["details"]
    assert user["password_hash"] not in log["details"]


# ── Prevention of Accidental Multiple Administrators ──

def test_prevent_accidental_multiple_initial_administrators(temp_user_store):
    # Create the first admin
    success1, _, user1 = bootstrap_admin(
        email="first_admin@finguard.ai",
        password="FirstAdmin123!",
        store=temp_user_store
    )
    assert success1

    # Attempt to bootstrap a second initial admin without allow_multiple flag
    success2, msg2, user2 = bootstrap_admin(
        email="second_admin@finguard.ai",
        password="SecondAdmin123!",
        allow_multiple=False,
        store=temp_user_store
    )
    assert not success2
    assert user2 is None
    assert "already exists in the system" in msg2
    assert "allow-multiple" in msg2

    # Now attempt with allow_multiple=True
    success3, _, user3 = bootstrap_admin(
        email="second_admin@finguard.ai",
        password="SecondAdmin123!",
        allow_multiple=True,
        store=temp_user_store
    )
    assert success3
    assert user3 is not None
    assert user3["role"] == "admin"


# ── Duplicate Accounts & Safe Non-Silent Handling ──

def test_existing_admin_account_without_reset_flag(temp_user_store):
    email = "admin123@gmail.com"
    success, _, _ = bootstrap_admin(
        email=email,
        password="InitialAdmin123!",
        store=temp_user_store
    )
    assert success

    # Re-running without reset_password flag should fail safely without altering account
    success_dup, msg_dup, existing = bootstrap_admin(
        email=email,
        password="DifferentPass123!",
        reset_password=False,
        store=temp_user_store
    )
    assert not success_dup
    assert "already exists" in msg_dup
    assert "--reset-password" in msg_dup

    # Verify initial password still works
    current_user = temp_user_store.get_user_by_email(email)
    assert verify_password("InitialAdmin123!", current_user["password_hash"])


def test_existing_standard_user_not_silently_promoted(temp_user_store):
    email = "standard_user@example.com"
    # Create regular user directly in store
    temp_user_store.create_user(
        email=email,
        password_hash="[DUMMY_HASH]",
        full_name="Normal User",
        role="user"
    )

    # Attempt bootstrap without promote flag
    success, msg, user = bootstrap_admin(
        email=email,
        password="NewAdminPass123!",
        promote=False,
        store=temp_user_store
    )
    assert not success
    assert "To prevent silent role elevation, specify --promote explicitly" in msg

    # Verify role was not changed silently
    check_user = temp_user_store.get_user_by_email(email)
    assert check_user["role"] == "user"


def test_existing_standard_user_explicit_promotion(temp_user_store):
    email = "promote_me@example.com"
    temp_user_store.create_user(
        email=email,
        password_hash="[OLD_HASH]",
        full_name="Promote User",
        role="user"
    )

    new_pass = "PromotedAdmin123!"
    success, msg, user = bootstrap_admin(
        email=email,
        password=new_pass,
        promote=True,
        store=temp_user_store
    )
    assert success
    assert user["role"] == "admin"
    assert verify_password(new_pass, user["password_hash"])

    # Verify audit log
    logs = temp_user_store.get_audit_logs()
    assert any(l["action"] == "promote_user_to_admin" and l["target_email"] == email for l in logs)


# ── Safe Administrator Password Reset ──

def test_safe_admin_password_reset(temp_user_store):
    email = "admin123@gmail.com"
    bootstrap_admin(
        email=email,
        password="OldSecureAdmin123!",
        store=temp_user_store
    )

    new_password = "NewSecureAdmin456!"
    success, msg, updated = bootstrap_admin(
        email=email,
        password=new_password,
        reset_password=True,
        store=temp_user_store
    )
    assert success
    assert "Successfully reset password" in msg

    user = temp_user_store.get_user_by_email(email)
    assert verify_password(new_password, user["password_hash"])
    assert not verify_password("OldSecureAdmin123!", user["password_hash"])

    # Audit log check
    logs = temp_user_store.get_audit_logs()
    reset_logs = [l for l in logs if l["action"] == "reset_admin_password"]
    assert len(reset_logs) == 1
    assert reset_logs[0]["target_email"] == email
    assert new_password not in reset_logs[0]["details"]
    assert user["password_hash"] not in reset_logs[0]["details"]
