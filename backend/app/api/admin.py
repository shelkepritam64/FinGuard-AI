from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status

from app.schemas.auth import (
    UserProfileResponse,
    AdminUserUpdateRequest,
    AdminCreateUserRequest,
    AuditLogEntry,
    UsageSummary
)
from app.services.user_store import user_store
from app.services.registry import registry_service
from app.core.auth import require_admin, hash_password

admin_router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@admin_router.get("/users")
def get_users(
    search: Optional[str] = Query(None, description="Search by email or name"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List and search registered users with pagination (Admin only)."""
    users, total = user_store.list_users(search=search, offset=offset, limit=limit)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "users": [
            UserProfileResponse(
                id=u["id"],
                email=u["email"],
                full_name=u["full_name"],
                role=u["role"],
                status=u["status"],
                created_at=u["created_at"],
                last_activity=u.get("last_activity"),
                screening_count=u["screening_count"],
                csv_count=u["csv_count"]
            )
            for u in users
        ]
    }


@admin_router.post("/users", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(payload: AdminCreateUserRequest, current_user: dict = Depends(require_admin)):
    """Create a new user with specific role and status (Admin only)."""
    clean_email = payload.email.strip().lower()
    if user_store.get_user_by_email(clean_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists."
        )

    pwd_hash = hash_password(payload.password)
    user = user_store.create_user(
        email=clean_email,
        password_hash=pwd_hash,
        full_name=payload.full_name,
        role=payload.role.value,
        status=payload.status.value
    )

    user_store.record_audit_log(
        actor_email=current_user["email"],
        action="admin_create_user",
        target_email=clean_email,
        details=f"Created with role '{payload.role.value}' and status '{payload.status.value}'"
    )

    return UserProfileResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        status=user["status"],
        created_at=user["created_at"],
        last_activity=None,
        screening_count=user["screening_count"],
        csv_count=user["csv_count"]
    )


@admin_router.patch("/users/{user_id}", response_model=UserProfileResponse)
def admin_update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    current_user: dict = Depends(require_admin)
):
    """Update user role or status (active/suspended) (Admin only)."""
    target = user_store.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    # Guard: Do not allow admin to suspend or demote their own active session
    if target["id"] == current_user["id"]:
        if payload.status and payload.status.value == "suspended":
            raise HTTPException(
                status_code=400,
                detail="Administrators cannot suspend their own active account."
            )
        if payload.role and payload.role.value != "admin":
            raise HTTPException(
                status_code=400,
                detail="Administrators cannot demote their own account. Have another administrator perform this action."
            )

    updated = user_store.update_user(
        user_id=user_id,
        role=payload.role.value if payload.role else None,
        status=payload.status.value if payload.status else None
    )

    details = []
    if payload.role:
        details.append(f"role -> {payload.role.value}")
    if payload.status:
        details.append(f"status -> {payload.status.value}")

    user_store.record_audit_log(
        actor_email=current_user["email"],
        action="admin_update_user",
        target_email=target["email"],
        details=", ".join(details)
    )

    return UserProfileResponse(
        id=updated["id"],
        email=updated["email"],
        full_name=updated["full_name"],
        role=updated["role"],
        status=updated["status"],
        created_at=updated["created_at"],
        last_activity=target.get("last_activity"),
        screening_count=updated["screening_count"],
        csv_count=updated["csv_count"]
    )


@admin_router.delete("/users/{user_id}")
def admin_delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    """Delete a user account and associated usage events (Admin only)."""
    target = user_store.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if target["id"] == current_user["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own administrative account via this endpoint."
        )

    user_store.delete_user(user_id)
    user_store.record_audit_log(
        actor_email=current_user["email"],
        action="admin_delete_user",
        target_email=target["email"],
        details=f"Deleted account {user_id}"
    )

    return {"status": "deleted", "message": f"User {target['email']} deleted successfully."}


@admin_router.get("/analytics")
def get_analytics(days: int = Query(14, ge=1, le=90, description="Timeline window in days")):
    """Aggregate usage counts, model utilization, and activity timeline (Admin only)."""
    summary = user_store.get_usage_summary()
    by_model = user_store.get_usage_by_model()
    timeline = user_store.get_usage_timeline(limit=days)

    return {
        "summary": summary,
        "by_model": by_model,
        "timeline": timeline
    }


@admin_router.get("/audit-logs", response_model=List[AuditLogEntry])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search audit records by actor, action, target, or details")
):
    """Retrieve immutable audit log of administrative actions (Admin only)."""
    logs = user_store.get_audit_logs(limit=limit, offset=offset, search=search)
    return [
        AuditLogEntry(
            id=log["id"],
            timestamp=log["timestamp"],
            actor_email=log["actor_email"],
            action=log["action"],
            target_email=log.get("target_email"),
            details=log.get("details")
        )
        for log in logs
    ]


@admin_router.get("/models-status")
def get_models_status():
    """Overview of registered models, availability, test metrics, and prediction counters (Admin only)."""
    models = registry_service.list_models()
    usage_by_model = {m["model_id"]: m for m in user_store.get_usage_by_model()}

    augmented_models = []
    for model in models:
        m_dict = model.model_dump()
        model_usage = usage_by_model.get(model.model_id, {})
        m_dict["total_predictions"] = model_usage.get("total_transactions", 0)
        m_dict["total_runs"] = model_usage.get("call_count", 0)
        m_dict["total_flagged"] = model_usage.get("total_flagged", 0)
        m_dict["successful_requests"] = model_usage.get("successful_requests", model_usage.get("call_count", 0))
        m_dict["failed_requests"] = model_usage.get("failed_requests", 0)
        augmented_models.append(m_dict)

    return {
        "total_models": len(augmented_models),
        "models": augmented_models,
        "metrics_note": "Metrics are offline test set evaluations (ROC-AUC, F1, Precision, Recall, PR-AUC). They represent laboratory benchmarks, not live production fraud capture rates."
    }

