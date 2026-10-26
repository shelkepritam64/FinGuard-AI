import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.routes import api_router
from app.api.auth import auth_router
from app.api.admin import admin_router
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler

logger = logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "finguard-ai-super-secret-jwt-key-for-local-development-change-in-prod"


def create_app() -> FastAPI:
    """Application factory for FinGuard AI Backend."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Educational transaction fraud-risk screening application backend."
    )

    # Attach rate limiter state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Configure CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routes under /api and /api/v1
    for prefix in ("/api", "/api/v1"):
        app.include_router(api_router, prefix=prefix)
        app.include_router(auth_router, prefix=prefix)
        app.include_router(admin_router, prefix=prefix)

    @app.on_event("startup")
    def startup_warnings():
        if settings.JWT_SECRET_KEY == _DEFAULT_JWT_SECRET:
            logger.warning(
                "\n"
                "⚠️  SECURITY WARNING: Using the default JWT secret key.\n"
                "   This is acceptable for local development, but MUST be changed in production.\n"
                "   Set JWT_SECRET_KEY in your .env file to a secure random 256-bit value.\n"
            )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
