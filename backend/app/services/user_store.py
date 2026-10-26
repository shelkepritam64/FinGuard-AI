import sqlite3
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from app.config import settings

logger = logging.getLogger(__name__)


class UserStore:
    """
    Lightweight, secure, and privacy-compliant user and usage data store.
    Supports Amazon DynamoDB for AWS deployments and embedded SQLite for local development.
    Never stores plaintext passwords, raw transaction inputs, or uploaded CSV payloads.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.resolved_local_db_path
        self.is_aws = (settings.STORAGE_BACKEND.lower() == "aws")
        self._dynamodb = None
        self._ensure_db_dir()
        self.init_db()

    def _get_dynamodb_resource(self):
        if self._dynamodb is None:
            self._dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
        return self._dynamodb

    def _ensure_db_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database schema if not already present."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    screening_count INTEGER NOT NULL DEFAULT 0,
                    csv_count INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Audit logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    actor_email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_email TEXT,
                    details TEXT
                )
            """)

            # Anonymized usage events table (tracks count, model, dataset, timestamp — NO raw features)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    row_count INTEGER NOT NULL DEFAULT 1,
                    flagged_count INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Screening history table (persisted in SQLite, privacy-safe metadata only, zero feature payloads)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screening_history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    screening_type TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    score_type TEXT,
                    prediction_score REAL,
                    threshold REAL,
                    risk_classification TEXT,
                    request_status TEXT NOT NULL DEFAULT 'completed',
                    row_count INTEGER NOT NULL DEFAULT 1,
                    flagged_count INTEGER NOT NULL DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)

            # Indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_events(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON screening_history(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON screening_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_type ON screening_history(screening_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_risk ON screening_history(risk_classification)")

            conn.commit()

    def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str,
        role: str = "user",
        status: str = "active"
    ) -> Dict[str, Any]:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        clean_email = email.strip().lower()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name, role, status, created_at, screening_count, csv_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (user_id, clean_email, password_hash, full_name.strip(), role, status, created_at)
            )
            conn.commit()

        return self.get_user_by_id(user_id)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def update_user(
        self,
        user_id: str,
        role: Optional[str] = None,
        status: Optional[str] = None,
        full_name: Optional[str] = None,
        password_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        fields = []
        params = []
        if role is not None:
            fields.append("role = ?")
            params.append(role)
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if full_name is not None:
            fields.append("full_name = ?")
            params.append(full_name.strip())
        if password_hash is not None:
            fields.append("password_hash = ?")
            params.append(password_hash)

        if not fields:
            return self.get_user_by_id(user_id)

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()

        return self.get_user_by_id(user_id)

    def count_admin_users(self) -> int:
        """Return the count of administrators in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            row = cursor.fetchone()
            return row[0] if row else 0

    def delete_user(self, user_id: str) -> bool:
        # Purge any saved reports in storage (S3 or local) for this user
        try:
            from app.services.storage import storage_service
            storage_service.delete_all_user_reports(user_id)
        except Exception:
            pass

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cursor.execute("DELETE FROM usage_events WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM screening_history WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_users(
        self,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            base_query = """
                SELECT u.id, u.email, u.full_name, u.role, u.status, u.created_at, u.screening_count, u.csv_count,
                       act.last_activity
                FROM users u
                LEFT JOIN (
                    SELECT user_id, MAX(timestamp) as last_activity
                    FROM (
                        SELECT user_id, timestamp FROM screening_history
                        UNION ALL
                        SELECT user_id, timestamp FROM usage_events
                    )
                    GROUP BY user_id
                ) act ON u.id = act.user_id
            """
            if search:
                term = f"%{search.strip().lower()}%"
                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE email LIKE ? OR full_name LIKE ?",
                    (term, term)
                )
                total = cursor.fetchone()[0]

                cursor.execute(
                    f"{base_query} WHERE u.email LIKE ? OR u.full_name LIKE ? ORDER BY u.created_at DESC LIMIT ? OFFSET ?",
                    (term, term, limit, offset)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM users")
                total = cursor.fetchone()[0]

                cursor.execute(
                    f"{base_query} ORDER BY u.created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )

            users = [dict(row) for row in cursor.fetchall()]
            return users, total

    def increment_user_usage(
        self,
        user_id: str,
        screening_increment: int = 0,
        csv_increment: int = 0
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET screening_count = screening_count + ?,
                    csv_count = csv_count + ?
                WHERE id = ?
                """,
                (screening_increment, csv_increment, user_id)
            )
            conn.commit()

    def record_usage_event(
        self,
        user_id: str,
        event_type: str,
        dataset_id: str,
        model_id: str,
        row_count: int = 1,
        flagged_count: int = 0
    ):
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO usage_events (id, user_id, event_type, dataset_id, model_id, timestamp, row_count, flagged_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, user_id, event_type, dataset_id, model_id, now, row_count, flagged_count)
            )
            conn.commit()

    def record_screening_history(
        self,
        user_id: str,
        screening_type: str,
        dataset_id: str,
        model_id: str,
        score_type: Optional[str] = None,
        prediction_score: Optional[float] = None,
        threshold: Optional[float] = None,
        risk_classification: Optional[str] = None,
        request_status: str = "completed",
        row_count: int = 1,
        flagged_count: int = 0
    ) -> Dict[str, Any]:
        """
        Record a privacy-safe screening history event for an authenticated user.
        Never stores raw transaction inputs, credit cards, or CSV payloads.
        """
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO screening_history (
                    id, user_id, screening_type, dataset_id, model_id,
                    score_type, prediction_score, threshold, risk_classification,
                    request_status, row_count, flagged_count, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, user_id, screening_type, dataset_id, model_id,
                    score_type, prediction_score, threshold, risk_classification,
                    request_status, row_count, flagged_count, now
                )
            )
            conn.commit()
        return {
            "id": event_id,
            "user_id": user_id,
            "screening_type": screening_type,
            "dataset_id": dataset_id,
            "model_id": model_id,
            "score_type": score_type,
            "prediction_score": prediction_score,
            "threshold": threshold,
            "risk_classification": risk_classification,
            "request_status": request_status,
            "row_count": row_count,
            "flagged_count": flagged_count,
            "timestamp": now
        }

    def get_user_screening_history(
        self,
        user_id: str,
        search: Optional[str] = None,
        screening_type: Optional[str] = None,
        risk_classification: Optional[str] = None,
        dataset_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve paginated, filtered screening history strictly for the authenticated user_id.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            where_clauses = ["user_id = ?"]
            params: List[Any] = [user_id]

            if screening_type and screening_type.lower() != "all":
                where_clauses.append("screening_type = ?")
                params.append(screening_type)

            if risk_classification and risk_classification.lower() != "all":
                where_clauses.append("risk_classification = ?")
                params.append(risk_classification)

            if dataset_id and dataset_id.lower() != "all":
                where_clauses.append("dataset_id = ?")
                params.append(dataset_id)

            if search and search.strip():
                term = f"%{search.strip().lower()}%"
                where_clauses.append("(LOWER(model_id) LIKE ? OR LOWER(dataset_id) LIKE ? OR LOWER(risk_classification) LIKE ? OR LOWER(score_type) LIKE ?)")
                params.extend([term, term, term, term])

            where_sql = " AND ".join(where_clauses)

            count_query = f"SELECT COUNT(*) FROM screening_history WHERE {where_sql}"
            cursor.execute(count_query, tuple(params))
            total = cursor.fetchone()[0]

            data_query = f"""
                SELECT id, user_id, screening_type, dataset_id, model_id,
                       score_type, prediction_score, threshold, risk_classification,
                       request_status, row_count, flagged_count, timestamp
                FROM screening_history
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            data_params = params + [limit, offset]
            cursor.execute(data_query, tuple(data_params))
            rows = [dict(row) for row in cursor.fetchall()]

            return rows, total

    def clear_user_history(self, user_id: str) -> bool:
        """Clear all screening history for an authenticated user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM screening_history WHERE user_id = ?", (user_id,))
            conn.commit()
            return True

    def record_audit_log(
        self,
        actor_email: str,
        action: str,
        target_email: Optional[str] = None,
        details: Optional[str] = None
    ):
        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_logs (id, timestamp, actor_email, action, target_email, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (log_id, now, actor_email, action, target_email, details)
            )
            conn.commit()

    def get_audit_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search and search.strip():
                term = f"%{search.strip().lower()}%"
                cursor.execute(
                    """
                    SELECT id, timestamp, actor_email, action, target_email, details
                    FROM audit_logs
                    WHERE LOWER(actor_email) LIKE ? OR LOWER(action) LIKE ? OR LOWER(target_email) LIKE ? OR LOWER(details) LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (term, term, term, term, limit, offset)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, timestamp, actor_email, action, target_email, details
                    FROM audit_logs
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
            rows = [dict(row) for row in cursor.fetchall()]
            return rows

    def get_usage_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
            active_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_users = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(screening_count), 0), COALESCE(SUM(csv_count), 0) FROM users")
            row = cursor.fetchone()
            total_screenings = row[0]
            total_csv_screenings = row[1]

            # Calculate active users over 7 days and 30 days
            now_dt = datetime.now(timezone.utc)
            cutoff_7d = (now_dt - timedelta(days=7)).isoformat()
            cutoff_30d = (now_dt - timedelta(days=30)).isoformat()

            cursor.execute(
                """
                SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT user_id, timestamp FROM screening_history WHERE user_id != 'anonymous'
                    UNION ALL
                    SELECT user_id, timestamp FROM usage_events WHERE user_id != 'anonymous'
                ) WHERE timestamp >= ?
                """,
                (cutoff_7d,)
            )
            active_users_7d = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT user_id, timestamp FROM screening_history WHERE user_id != 'anonymous'
                    UNION ALL
                    SELECT user_id, timestamp FROM usage_events WHERE user_id != 'anonymous'
                ) WHERE timestamp >= ?
                """,
                (cutoff_30d,)
            )
            active_users_30d = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM screening_history WHERE request_status = 'failed'"
            )
            api_errors = cursor.fetchone()[0]

            return {
                "total_users": total_users,
                "active_users": active_users,
                "active_users_7d": active_users_7d,
                "active_users_30d": active_users_30d,
                "admin_users": admin_users,
                "total_screenings": total_screenings,
                "total_csv_screenings": total_csv_screenings,
                "api_errors": api_errors,
                "system_health": "healthy"
            }

    def get_usage_by_model(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT model_id, dataset_id,
                       COUNT(*) as call_count,
                       SUM(row_count) as total_transactions,
                       SUM(flagged_count) as total_flagged,
                       SUM(CASE WHEN request_status = 'completed' THEN 1 ELSE 0 END) as successful_requests,
                       SUM(CASE WHEN request_status = 'failed' THEN 1 ELSE 0 END) as failed_requests
                FROM (
                    SELECT model_id, dataset_id, row_count, flagged_count, request_status FROM screening_history
                    UNION ALL
                    SELECT model_id, dataset_id, row_count, flagged_count, 'completed' as request_status FROM usage_events
                )
                GROUP BY model_id, dataset_id
                ORDER BY call_count DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_usage_timeline(self, limit: int = 14) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT SUBSTR(timestamp, 1, 10) as date,
                       COUNT(*) as event_count,
                       SUM(row_count) as total_volume,
                       SUM(CASE WHEN request_status = 'failed' THEN 1 ELSE 0 END) as failed_count
                FROM (
                    SELECT timestamp, row_count, request_status FROM screening_history
                    UNION ALL
                    SELECT timestamp, row_count, 'completed' as request_status FROM usage_events
                )
                GROUP BY SUBSTR(timestamp, 1, 10)
                ORDER BY date DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]


user_store = UserStore()
