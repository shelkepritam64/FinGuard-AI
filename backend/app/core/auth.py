import logging
import urllib.request
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import bcrypt
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.services.user_store import user_store

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)

# Cached JWKS client for Cognito
_cognito_jwks_client: Optional[PyJWKClient] = None


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a local signed JWT with issuer, audience, and expiration."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_local_token(token: str) -> Dict[str, Any]:
    """Validate and decode a locally signed JWT."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE
    )


def decode_cognito_token(token: str) -> Dict[str, Any]:
    """
    Validate and decode an Amazon Cognito ID/Access token.
    Validates RSA signature from AWS JWKS, audience, issuer, and expiry.
    """
    global _cognito_jwks_client
    if not settings.COGNITO_USER_POOL_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cognito User Pool ID is not configured."
        )

    jwks_url = f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    expected_issuer = f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}"

    if _cognito_jwks_client is None:
        _cognito_jwks_client = PyJWKClient(jwks_url)

    try:
        signing_key = _cognito_jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=expected_issuer,
            audience=settings.COGNITO_APP_CLIENT_ID if settings.COGNITO_APP_CLIENT_ID else None,
            options={"verify_aud": bool(settings.COGNITO_APP_CLIENT_ID)}
        )
        return payload
    except Exception as e:
        logger.error(f"Cognito token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Cognito token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def verify_token(token: str) -> Dict[str, Any]:
    """Dispatch token verification to configured provider (local or cognito)."""
    if settings.AUTH_PROVIDER.lower() == "cognito":
        payload = decode_cognito_token(token)
        # Extract role from cognito:groups claim if present
        groups = payload.get("cognito:groups", [])
        role = "admin" if "admin" in groups or "admins" in groups else "user"
        user_id = payload.get("sub")
        email = payload.get("email", "")
        return {
            "sub": user_id,
            "email": email,
            "role": role,
            "raw_payload": payload
        }
    else:
        try:
            return decode_local_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Dict[str, Any]:
    """FastAPI dependency to extract and verify the current authenticated user."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # In local mode, fetch user from DB to verify active status and actual current role
    user = user_store.get_user_by_id(user_id)
    if not user:
        # Fallback by email if sub was not UUID or for Cognito
        email = payload.get("email")
        if email:
            user = user_store.get_user_by_email(email)

    if not user:
        if settings.AUTH_PROVIDER.lower() == "cognito":
            # Auto-provision local shadow user for Cognito if valid token presented
            user = user_store.create_user(
                email=payload.get("email", f"{user_id}@cognito.aws"),
                password_hash="[COGNITO_MANAGED]",
                full_name=payload.get("email", "Cognito User").split("@")[0],
                role=payload.get("role", "user")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists.",
                headers={"WWW-Authenticate": "Bearer"}
            )

    if user.get("status") == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact an administrator."
        )

    return user


def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Optional[Dict[str, Any]]:
    """Optional authentication dependency: returns user dict if valid token, else None."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


def require_role(allowed_roles: List[str]):
    """Role-based access control dependency factory."""
    def role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "user")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This action requires one of the following roles: {allowed_roles}. Your role is '{user_role}'."
            )
        return current_user
    return role_dependency


require_admin = require_role(["admin"])
require_authenticated = get_current_user
