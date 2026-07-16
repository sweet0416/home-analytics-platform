from datetime import datetime

from app.core.backup import scheduler
from app.core.backup.remote import RemoteBackupResult


class _FakeGithubBackupClient:
    def __init__(self, settings: object) -> None:
        self._settings = settings

    def upload_encrypted_backup(self, backup_path: object) -> RemoteBackupResult:
        return RemoteBackupResult(
            enabled=True,
            configured=True,
            status="success",
            message="Uploaded encrypted backup: hap_test.db.gz.enc",
            asset_name="hap_test.db.gz.enc",
            uploaded_at=datetime(2026, 7, 16, 21, 20, 0),
        )

    def status(self) -> dict[str, object]:
        return {
            "enabled": True,
            "configured": True,
            "repo": "sweet0416/hap-backups",
            "release_tag": "hap-backups",
        }


def test_upload_remote_backup_records_latest_status(monkeypatch, tmp_path) -> None:
    backup_path = tmp_path / "hap_test.db"
    backup_path.write_bytes(b"sqlite")
    monkeypatch.setattr(scheduler, "GithubBackupClient", _FakeGithubBackupClient)

    result = scheduler.upload_remote_backup(backup_path)
    status = scheduler.get_backup_scheduler_status()

    assert result.status == "success"
    assert status["remote"]["last_status"] == "success"
    assert status["remote"]["last_asset_name"] == "hap_test.db.gz.enc"
    assert status["remote"]["last_uploaded_at"] == "2026-07-16T21:20:00"
