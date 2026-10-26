import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.storage import storage_service
from app.core.auth import create_access_token
from app.services.user_store import user_store

client = TestClient(app)


def test_storage_user_isolation_prevent_cross_user_access():
    user_a = "user-aaa-111"
    user_b = "user-bbb-222"

    report_a = storage_service.save_report(
        user_id=user_a,
        filename="batch_screening.csv",
        csv_content="col1,col2,prediction_score\n1,2,0.95\n"
    )

    report_key_a = report_a["storage_path"]
    assert report_key_a.startswith(f"reports/{user_a}/")

    # User A can generate download URL for their own report
    url_a = storage_service.generate_download_url(user_id=user_a, report_key=report_key_a)
    assert url_a is not None

    # User B attempting to access User A's report key MUST be denied
    with pytest.raises(PermissionError) as exc_info:
        storage_service.generate_download_url(user_id=user_b, report_key=report_key_a)
    assert "Access denied" in str(exc_info.value)


def test_storage_listing_and_deletion_isolation():
    user_x = "user-xxx-isolation"
    user_y = "user-yyy-isolation"

    rep1 = storage_service.save_report(user_id=user_x, filename="report1.csv", csv_content="a,b\n1,2\n")
    rep2 = storage_service.save_report(user_id=user_x, filename="report2.csv", csv_content="c,d\n3,4\n")
    rep_y = storage_service.save_report(user_id=user_y, filename="report_y.csv", csv_content="e,f\n5,6\n")

    # User X should only see their 2 reports
    list_x = storage_service.list_reports(user_id=user_x)
    filenames_x = [r["filename"] for r in list_x]
    assert len(list_x) >= 2
    assert any("report1.csv" in fn for fn in filenames_x)
    assert any("report2.csv" in fn for fn in filenames_x)
    assert not any("report_y.csv" in fn for fn in filenames_x)

    # User Y cannot delete User X's report
    with pytest.raises(PermissionError):
        storage_service.delete_report(user_id=user_y, report_key=rep1["storage_path"])

    # User X can delete their report
    deleted = storage_service.delete_report(user_id=user_x, report_key=rep1["storage_path"])
    assert deleted is True


def test_reports_api_endpoints_with_auth_and_ownership():
    user1 = user_store.get_user_by_email("u1_rep@test.com")
    if not user1:
        user1 = user_store.create_user("u1_rep@test.com", "hash1", "User One")
    user2 = user_store.get_user_by_email("u2_rep@test.com")
    if not user2:
        user2 = user_store.create_user("u2_rep@test.com", "hash2", "User Two")

    token_u1 = create_access_token({"sub": user1["id"], "email": user1["email"], "role": "user"})
    token_u2 = create_access_token({"sub": user2["id"], "email": user2["email"], "role": "user"})

    # 1. Unauthenticated cannot save report
    unauth_resp = client.post("/api/reports/save", json={"filename": "test.csv", "csv_content": "a,b\n1,2"})
    assert unauth_resp.status_code == 401

    # 2. User 1 saves a report
    save_resp = client.post(
        "/api/reports/save",
        json={"filename": "user1_report.csv", "csv_content": "col1,score\nval1,0.99\n"},
        headers={"Authorization": f"Bearer {token_u1}"}
    )
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["storage_path"].startswith(f"reports/{user1['id']}/")
    report_key = save_data["storage_path"]

    # 3. User 1 lists reports
    list_resp = client.get("/api/reports", headers={"Authorization": f"Bearer {token_u1}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 4. User 2 cannot download User 1's report (403 Forbidden)
    cross_download = client.get(
        f"/api/reports/download?key={report_key}",
        headers={"Authorization": f"Bearer {token_u2}"}
    )
    assert cross_download.status_code == 403
    assert "Access denied" in cross_download.json()["detail"]

    # 5. User 1 can download their report
    valid_download = client.get(
        f"/api/reports/download?key={report_key}",
        headers={"Authorization": f"Bearer {token_u1}"}
    )
    assert valid_download.status_code == 200

    # 6. User 2 cannot delete User 1's report (403 Forbidden)
    cross_delete = client.delete(
        f"/api/reports?key={report_key}",
        headers={"Authorization": f"Bearer {token_u2}"}
    )
    assert cross_delete.status_code == 403

    # 7. User 1 deletes their report
    valid_delete = client.delete(
        f"/api/reports?key={report_key}",
        headers={"Authorization": f"Bearer {token_u1}"}
    )
    assert valid_delete.status_code == 200
    assert valid_delete.json()["status"] == "deleted"


# ── Mocked AWS Cloud Storage Tests ──

from unittest.mock import MagicMock, patch


def test_mocked_aws_s3_save_and_download():
    """Verify S3 client interactions, AES256 server-side encryption, and ownership validation in AWS mode."""
    with patch.object(storage_service, "_get_s3_client") as mock_get_client:
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/presigned-url"

        storage_service.is_aws = True
        storage_service.bucket_name = "finguard-test-private-reports"

        try:
            user_id = "aws-user-123"
            res = storage_service.save_report(
                user_id=user_id,
                filename="aws_export.csv",
                csv_content="f1,f2,score\n1,2,0.99\n"
            )

            # 1. Assert put_object was called with encryption and user namespace
            mock_s3.put_object.assert_called_once()
            call_kwargs = mock_s3.put_object.call_args[1]
            assert call_kwargs["Bucket"] == "finguard-test-private-reports"
            assert call_kwargs["Key"].startswith(f"reports/{user_id}/")
            assert call_kwargs["ServerSideEncryption"] == "AES256"
            assert call_kwargs["ContentType"] == "text/csv"

            # 2. Assert presigned URL generation validates ownership
            url = storage_service.generate_download_url(user_id=user_id, report_key=res["storage_path"])
            assert "https://s3.amazonaws.com" in url
            mock_s3.generate_presigned_url.assert_called_once()

            # 3. Cross-user presigned URL attempt is blocked before touching S3
            with pytest.raises(PermissionError) as exc:
                storage_service.generate_download_url(user_id="another-user", report_key=res["storage_path"])
            assert "Access denied" in str(exc.value)

        finally:
            storage_service.is_aws = False


def test_mocked_aws_s3_delete_and_purge():
    """Verify S3 delete_object and paginated purge operations in AWS mode."""
    with patch.object(storage_service, "_get_s3_client") as mock_get_client:
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        # Mock paginator for list_objects_v2
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "reports/purge-user/r1.csv"}, {"Key": "reports/purge-user/r2.csv"}]}
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        storage_service.is_aws = True
        storage_service.bucket_name = "finguard-test-private-reports"

        try:
            # 1. Individual delete
            del_success = storage_service.delete_report(user_id="purge-user", report_key="reports/purge-user/r1.csv")
            assert del_success is True
            mock_s3.delete_object.assert_called_with(
                Bucket="finguard-test-private-reports",
                Key="reports/purge-user/r1.csv"
            )

            # 2. Cross-user delete rejected
            with pytest.raises(PermissionError):
                storage_service.delete_report(user_id="attacker", report_key="reports/purge-user/r1.csv")

            # 3. Purge all reports for user
            purged_count = storage_service.delete_all_user_reports(user_id="purge-user")
            assert purged_count == 2
            mock_s3.delete_objects.assert_called_once()
            del_args = mock_s3.delete_objects.call_args[1]
            assert del_args["Bucket"] == "finguard-test-private-reports"
            assert len(del_args["Delete"]["Objects"]) == 2

        finally:
            storage_service.is_aws = False


