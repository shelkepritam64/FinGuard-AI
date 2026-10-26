import io
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

import boto3
from botocore.exceptions import ClientError
from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Manages optional persistence for explicitly saved reports and approved exports.
    Adheres strictly to AWS security best practices:
      - Private S3 bucket with Block Public Access
      - Server-Side Encryption (AES256)
      - Least-privilege key paths partitioned by user_id: reports/{user_id}/{report_id}.csv
      - User ownership verification before granting presigned URLs
      - Never stores credentials, passwords, or raw unsaved transactions
    """

    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.is_aws = (
            settings.STORAGE_BACKEND.lower() == "aws"
            and bool(self.bucket_name)
        )
        self._s3_client = None

    def _get_s3_client(self):
        if self._s3_client is None:
            self._s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
        return self._s3_client

    def save_report(
        self,
        user_id: str,
        filename: str,
        csv_content: str,
        summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Explicitly persist a CSV prediction screening report.
        Strictly requires authenticated user_id for namespace isolation.
        """
        report_id = str(uuid.uuid4())
        safe_filename = Path(filename).name.replace(" ", "_")
        s3_key = f"reports/{user_id}/{report_id}_{safe_filename}"
        timestamp = datetime.now(timezone.utc).isoformat()

        if self.is_aws:
            try:
                client = self._get_s3_client()
                client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=csv_content.encode("utf-8"),
                    ContentType="text/csv",
                    ServerSideEncryption="AES256",
                    Metadata={
                        "user_id": user_id,
                        "report_id": report_id,
                        "created_at": timestamp
                    }
                )
            except ClientError as e:
                logger.error(f"S3 put_object error: {e}")
                raise RuntimeError("Failed to persist report to secure cloud storage.")
        else:
            # Local fallback storage in backend data folder
            local_dir = settings.resolved_local_db_path.parent / "reports" / user_id
            local_dir.mkdir(parents=True, exist_ok=True)
            local_file = local_dir / f"{report_id}_{safe_filename}"
            with open(local_file, "w", encoding="utf-8") as f:
                f.write(csv_content)

        return {
            "report_id": report_id,
            "filename": safe_filename,
            "storage_path": s3_key,
            "is_cloud": self.is_aws,
            "created_at": timestamp,
            "summary": summary or {}
        }

    def generate_download_url(self, user_id: str, report_key: str, expires_in: int = 3600) -> str:
        """
        Generate time-limited presigned URL for downloading explicitly saved report.
        Verifies ownership: report_key MUST start with 'reports/{user_id}/'.
        """
        # Strict user-namespace check prevents accessing other users' files
        expected_prefix = f"reports/{user_id}/"
        if not report_key.startswith(expected_prefix):
            raise PermissionError("Access denied: You do not own this storage object.")

        if self.is_aws:
            try:
                client = self._get_s3_client()
                return client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": report_key,
                        "ResponseContentDisposition": "attachment"
                    },
                    ExpiresIn=expires_in
                )
            except ClientError as e:
                logger.error(f"S3 generate_presigned_url error: {e}")
                raise RuntimeError("Failed to generate secure presigned download link.")
        else:
            return f"/api/reports/download?key={report_key}"

    def list_reports(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List saved reports belonging strictly to the specified user_id.
        Enforces user namespace isolation.
        """
        prefix = f"reports/{user_id}/"
        results = []

        if self.is_aws:
            try:
                client = self._get_s3_client()
                paginator = client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    for item in page.get("Contents", []):
                        key = item["Key"]
                        # Extract report_id and filename
                        filename_part = key[len(prefix):]
                        results.append({
                            "storage_path": key,
                            "filename": filename_part,
                            "size_bytes": item.get("Size", 0),
                            "last_modified": item.get("LastModified", "").isoformat() if hasattr(item.get("LastModified"), "isoformat") else str(item.get("LastModified", "")),
                            "is_cloud": True
                        })
            except ClientError as e:
                logger.error(f"S3 list_objects_v2 error: {e}")
                return []
        else:
            local_dir = settings.resolved_local_db_path.parent / "reports" / user_id
            if local_dir.exists():
                for p in local_dir.glob("*"):
                    if p.is_file():
                        stat = p.stat()
                        results.append({
                            "storage_path": f"{prefix}{p.name}",
                            "filename": p.name,
                            "size_bytes": stat.st_size,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                            "is_cloud": False
                        })
        return results

    def delete_report(self, user_id: str, report_key: str) -> bool:
        """
        Delete a single report object.
        Enforces ownership: report_key must start with reports/{user_id}/.
        """
        expected_prefix = f"reports/{user_id}/"
        if not report_key.startswith(expected_prefix):
            raise PermissionError("Access denied: You do not own this storage object.")

        if self.is_aws:
            try:
                client = self._get_s3_client()
                client.delete_object(Bucket=self.bucket_name, Key=report_key)
                return True
            except ClientError as e:
                logger.error(f"S3 delete_object error: {e}")
                return False
        else:
            filename_part = report_key[len(expected_prefix):]
            local_file = settings.resolved_local_db_path.parent / "reports" / user_id / filename_part
            if local_file.exists():
                local_file.unlink()
                return True
            return False

    def delete_all_user_reports(self, user_id: str) -> int:
        """
        Purge all reports for a user during account deletion.
        """
        prefix = f"reports/{user_id}/"
        deleted_count = 0

        if self.is_aws:
            try:
                client = self._get_s3_client()
                paginator = client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    objects_to_delete = [{"Key": item["Key"]} for item in page.get("Contents", [])]
                    if objects_to_delete:
                        client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={"Objects": objects_to_delete}
                        )
                        deleted_count += len(objects_to_delete)
            except ClientError as e:
                logger.error(f"S3 delete_objects error during account deletion: {e}")
        else:
            local_dir = settings.resolved_local_db_path.parent / "reports" / user_id
            if local_dir.exists():
                for p in local_dir.glob("*"):
                    if p.is_file():
                        p.unlink()
                        deleted_count += 1
                try:
                    local_dir.rmdir()
                except Exception:
                    pass
        return deleted_count

    def get_report_content(self, user_id: str, report_key: str) -> str:
        """
        Read content of a saved report for streaming or downloading.
        Enforces ownership.
        """
        expected_prefix = f"reports/{user_id}/"
        if not report_key.startswith(expected_prefix):
            raise PermissionError("Access denied: You do not own this storage object.")

        if self.is_aws:
            try:
                client = self._get_s3_client()
                obj = client.get_object(Bucket=self.bucket_name, Key=report_key)
                return obj["Body"].read().decode("utf-8")
            except ClientError as e:
                logger.error(f"S3 get_object error: {e}")
                raise RuntimeError("Failed to retrieve report content from S3.")
        else:
            filename_part = report_key[len(expected_prefix):]
            local_file = settings.resolved_local_db_path.parent / "reports" / user_id / filename_part
            if not local_file.exists():
                raise FileNotFoundError("Requested report does not exist.")
            with open(local_file, "r", encoding="utf-8") as f:
                return f.read()


storage_service = StorageService()
