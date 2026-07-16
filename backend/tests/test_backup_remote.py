from datetime import datetime

from app.core.backup import scheduler
from app.core.backup.repository import DatabaseBackupRunRepository
from app.core.backup.remote import RemoteBackupResult
from app.core.backup.schemas import DatabaseBackupRead


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
    backup = DatabaseBackupRead(
        file_name="hap_test.db",
        size_bytes=6,
        created_at=datetime(2026, 7, 16, 21, 19, 0),
    )
    recorded: list[tuple[DatabaseBackupRead, str, RemoteBackupResult]] = []

    monkeypatch.setattr(scheduler, "GithubBackupClient", _FakeGithubBackupClient)
    monkeypatch.setattr(scheduler, "_get_latest_remote_run", lambda: {})
    monkeypatch.setattr(
        scheduler,
        "_record_backup_run",
        lambda backup, trigger_type, remote_result: recorded.append(
            (backup, trigger_type, remote_result)
        ),
    )

    result = scheduler.upload_remote_backup(
        backup=backup,
        backup_path=backup_path,
        trigger_type="manual",
    )
    status = scheduler.get_backup_scheduler_status()

    assert result.status == "success"
    assert status["remote"]["last_status"] == "success"
    assert status["remote"]["last_asset_name"] == "hap_test.db.gz.enc"
    assert status["remote"]["last_uploaded_at"] == "2026-07-16T21:20:00"
    assert recorded[0][1] == "manual"


def test_backup_run_repository_reads_latest_remote_run(db_session) -> None:
    repo = DatabaseBackupRunRepository(db_session)
    backup = DatabaseBackupRead(
        file_name="hap_test.db",
        size_bytes=6,
        created_at=datetime(2026, 7, 16, 21, 19, 0),
    )
    remote_result = RemoteBackupResult(
        enabled=True,
        configured=True,
        status="success",
        message="Uploaded encrypted backup: hap_test.db.gz.enc",
        asset_name="hap_test.db.gz.enc",
        uploaded_at=datetime(2026, 7, 16, 21, 20, 0),
    )

    repo.record_run(backup=backup, trigger_type="manual", remote_result=remote_result)
    latest = repo.get_latest_remote_run()

    assert latest is not None
    assert latest.trigger_type == "manual"
    assert latest.remote_status == "success"
    assert latest.remote_asset_name == "hap_test.db.gz.enc"
