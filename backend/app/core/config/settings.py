from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Home Analytics Platform"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    database_url: str = "sqlite:///./data/sqlite/hap.db"
    log_level: str = "INFO"
    log_dir: Path = Field(default=Path("logs"))
    backup_dir: Path = Field(default=Path("data/backups"))
    backup_retention_count: int = Field(default=30, ge=1, le=365)
    lottery_dlt_auto_sync_enabled: bool = True
    lottery_dlt_sync_cron: str = "30 22 * * *"
    lottery_dlt_sync_page_size: int = Field(default=100, ge=1, le=500)
    lottery_dlt_sync_timeout_seconds: int = Field(default=30, ge=5, le=120)
    lottery_dlt_fallback_enabled: bool = True
    lottery_dlt_sporttery_url: str = (
        "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    )
    lottery_dlt_500_history_url: str = (
        "https://datachart.500.com/dlt/history/newinc/history.php"
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
