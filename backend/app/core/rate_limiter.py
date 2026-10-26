"""
FinGuard AI — Rate Limiting Configuration
==========================================
Uses slowapi to protect authentication endpoints from brute-force attacks.
In-memory storage keeps local development simple with no extra infrastructure.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a user-friendly JSON error when rate limit is exceeded."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please wait before trying again.",
            "retry_after": str(exc.detail),
        },
    )
