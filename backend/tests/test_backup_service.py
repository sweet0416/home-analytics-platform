from pathlib import Path

from app.core.backup.service import DatabaseBackupService
from app.core.config.settings import Settings


def test_prepare_backup_directory_migrates_legacy_backups(tmp_path: Path) -> None:
    sqlite_dir = tmp_path / "sqlite"
    legacy_dir = sqlite_dir / "backups"
    backup_dir = tmp_path / "backups"
    legacy_dir.mkdir(parents=True)
    database_path = sqlite_dir / "hap.db"
    database_path.touch()
    legacy_file = legacy_dir / "hap_20260811_030000.db"
    legacy_file.write_bytes(b"legacy")

    service = DatabaseBackupService(
        Settings(
            database_url=f"sqlite:///{database_path}",
            backup_dir=backup_dir,
        )
    )

    result = service._prepare_backup_directory()

    assert result == backup_dir
    assert (backup_dir / legacy_file.name).read_bytes() == b"legacy"


def test_prepare_backup_directory_does_not_overwrite_existing_backup(tmp_path: Path) -> None:
    sqlite_dir = tmp_path / "sqlite"
    legacy_dir = sqlite_dir / "backups"
    backup_dir = tmp_path / "backups"
    legacy_dir.mkdir(parents=True)
    backup_dir.mkdir(parents=True)
    database_path = sqlite_dir / "hap.db"
    database_path.touch()
    backup_name = "hap_20260811_030000.db"
    (legacy_dir / backup_name).write_bytes(b"legacy")
    (backup_dir / backup_name).write_bytes(b"new")

    service = DatabaseBackupService(
        Settings(
            database_url=f"sqlite:///{database_path}",
            backup_dir=backup_dir,
        )
    )

    service._prepare_backup_directory()

    assert (backup_dir / backup_name).read_bytes() == b"new"
