from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class Role(str, Enum):
    user = "user"
    admin = "admin"


class AccountStatus(str, Enum):
    active = "active"
    suspended = "suspended"


def validate_email_str(v: str) -> str:
    cleaned = v.strip().lower()
    if "@" not in cleaned or "." not in cleaned.split("@")[-1] or len(cleaned) < 5:
        raise ValueError("Invalid email format. Must contain '@' and domain.")
    return cleaned


class UserRegisterRequest(BaseModel):
    """User self-registration. Note: role cannot be chosen by user, defaults to 'user'."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_str(v)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_str(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    user_id: str
    email: str
    full_name: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    created_at: str
    last_activity: Optional[str] = None
    screening_count: int = 0
    csv_count: int = 0


class AdminUserUpdateRequest(BaseModel):
    role: Optional[Role] = None
    status: Optional[AccountStatus] = None


class AdminCreateUserRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: Role = Role.user
    status: AccountStatus = AccountStatus.active

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_str(v)


class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    actor_email: str
    action: str
    target_email: Optional[str] = None
    details: Optional[str] = None


class UsageSummary(BaseModel):
    total_screenings: int = 0
    total_csv_screenings: int = 0
    total_users: int = 0
    active_users: int = 0
    active_users_7d: int = 0
    active_users_30d: int = 0
    admin_users: int = 0
    api_errors: int = 0
    system_health: str = "healthy"



class UsageEventRecord(BaseModel):
    id: str
    user_id: str
    event_type: str  # "single_screening" | "csv_batch"
    dataset_id: str
    model_id: str
    timestamp: str
    row_count: int = 1
    flagged_count: int = 0


class ScreeningHistoryItem(BaseModel):
    id: str
    user_id: str
    screening_type: str  # "single_screening" | "csv_batch"
    dataset_id: str
    model_id: str
    score_type: Optional[str] = None
    prediction_score: Optional[float] = None
    threshold: Optional[float] = None
    risk_classification: Optional[str] = None
    request_status: str = "completed"
    row_count: int = 1
    flagged_count: int = 0
    timestamp: str


class ScreeningHistoryResponse(BaseModel):
    total: int
    offset: int
    limit: int
    items: List[ScreeningHistoryItem]

