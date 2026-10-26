import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query, status

from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse,
    ScreeningHistoryResponse,
    ScreeningHistoryItem
)
from app.services.user_store import user_store
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.core.rate_limiter import limiter
from app.config import settings

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


def _validate_password_strength(password: str) -> None:
    """
    Enforce password-strength rules on the backend — never trust the frontend alone.
    Requires: ≥ 8 chars, ≥ 1 uppercase, ≥ 1 lowercase, ≥ 1 digit.
    """
    issues = []
    if len(password) < 8:
        issues.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        issues.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        issues.append("at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        issues.append("at least one digit")
    if issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must contain {', '.join(issues)}."
        )


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def register(request: Request, payload: UserRegisterRequest):
    """
    Self-register a standard user account.
    Role is strictly defaulted to 'user'; administrative role cannot be requested.
    Enforces password strength, email normalization, and duplicate rejection.
    """
    _validate_password_strength(payload.password)

    clean_email = payload.email.strip().lower()
    existing_user = user_store.get_user_by_email(clean_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )

    pwd_hash = hash_password(payload.password)
    user = user_store.create_user(
        email=clean_email,
        password_hash=pwd_hash,
        full_name=payload.full_name,
        role="user",
        status="active"
    )

    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"]
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user["role"],
        user_id=user["id"],
        email=user["email"],
        full_name=user["full_name"]
    )


@auth_router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: UserLoginRequest):
    """
    Authenticate with email and password and receive a secure JWT.
    Returns a generic error for invalid credentials to avoid user-enumeration.
    """
    clean_email = payload.email.strip().lower()
    user = user_store.get_user_by_email(clean_email)

    # Generic error message prevents user-enumeration
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if user["status"] == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact an administrator."
        )

    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"]
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user["role"],
        user_id=user["id"],
        email=user["email"],
        full_name=user["full_name"]
    )


@auth_router.post("/logout", status_code=status.HTTP_200_OK)
def logout(current_user: dict = Depends(get_current_user)):
    """
    Server-acknowledged logout.
    With stateless JWTs, the token remains valid until expiry — the frontend
    must delete the stored token. This endpoint provides a clear contract
    and audit-log hook for future token blacklisting.
    """
    user_store.record_audit_log(
        actor_email=current_user["email"],
        action="user_logout",
        details="User-initiated logout"
    )
    return {"status": "logged_out", "message": "Session has been cleared."}


@auth_router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Retrieve currently authenticated user profile and individual usage counters."""
    return UserProfileResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        status=current_user["status"],
        created_at=current_user["created_at"],
        screening_count=current_user["screening_count"],
        csv_count=current_user["csv_count"]
    )


@auth_router.delete("/me", status_code=status.HTTP_200_OK)
def delete_my_account(current_user: dict = Depends(get_current_user)):
    """Allow an authenticated user to delete their account and associated records."""
    user_store.record_audit_log(
        actor_email=current_user["email"],
        action="self_delete_account",
        target_email=current_user["email"],
        details="User initiated self-deletion"
    )
    user_store.delete_user(current_user["id"])
    return {"status": "deleted", "message": "Your account has been permanently deleted."}


@auth_router.get("/history", response_model=ScreeningHistoryResponse)
def get_user_history(
    search: Optional[str] = Query(None, description="Search by model, dataset, score type, or risk"),
    screening_type: Optional[str] = Query(None, description="Filter by screening type (single_screening, csv_batch)"),
    risk_classification: Optional[str] = Query(None, description="Filter by risk label (High Risk, Low Risk)"),
    dataset_id: Optional[str] = Query(None, description="Filter by dataset ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve server-verified screening history strictly for the authenticated user.
    Never accepts client-supplied user_id. Supports search, filtering, and pagination.
    """
    items, total = user_store.get_user_screening_history(
        user_id=current_user["id"],
        search=search,
        screening_type=screening_type,
        risk_classification=risk_classification,
        dataset_id=dataset_id,
        offset=offset,
        limit=limit
    )

    return ScreeningHistoryResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[ScreeningHistoryItem(**item) for item in items]
    )


@auth_router.delete("/history", status_code=status.HTTP_200_OK)
def clear_user_history(current_user: dict = Depends(get_current_user)):
    """Allow an authenticated user to clear their screening history."""
    user_store.clear_user_history(current_user["id"])
    return {"status": "cleared", "message": "Your screening history has been cleared."}

