from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FinGuard AI Backend Settings."""

    APP_NAME: str = "FinGuard AI API"
    APP_ENV: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Environment-based paths for model artifacts and datasets
    # Defaults resolve relative to the backend working directory
    MODELS_BASE_DIR: str = "../../model files/models"
    DATASETS_BASE_DIR: str = "../../dataset"

    # Upload constraints
    MAX_UPLOAD_SIZE_MB: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def resolved_models_dir(self) -> Path:
        base_path = Path(__file__).resolve().parent.parent
        candidate = Path(self.MODELS_BASE_DIR)
        if candidate.is_absolute():
            return candidate
        return (base_path / candidate).resolve()

    @property
    def resolved_datasets_dir(self) -> Path:
        base_path = Path(__file__).resolve().parent.parent
        candidate = Path(self.DATASETS_BASE_DIR)
        if candidate.is_absolute():
            return candidate
        return (base_path / candidate).resolve()


settings = Settings()
