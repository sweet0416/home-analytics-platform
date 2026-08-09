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
    backup_auto_enabled: bool = True
    backup_cron: str = "10 3 * * *"
    github_backup_enabled: bool = False
    github_backup_repo: str = ""
    github_backup_token: str = ""
    github_backup_release_tag: str = "hap-backups"
    github_backup_encryption_passphrase: str = ""
    github_backup_timeout_seconds: int = Field(default=30, ge=5, le=120)
    notification_timeout_seconds: int = Field(default=15, ge=3, le=60)
    notification_bark_enabled: bool = False
    notification_bark_server_url: str = "https://api.day.app"
    notification_bark_device_key: str = ""
    notification_bark_group: str = "HAP"
    notification_bark_sound: str = ""
    notification_bark_level: str = "active"
    notification_wecom_enabled: bool = False
    notification_wecom_webhook_url: str = ""
    notification_whatsapp_enabled: bool = False
    notification_whatsapp_graph_version: str = "v20.0"
    notification_whatsapp_phone_number_id: str = ""
    notification_whatsapp_access_token: str = ""
    notification_whatsapp_recipient_phone: str = ""
    notification_custom_webhook_enabled: bool = False
    notification_custom_webhook_url: str = ""
    notification_custom_webhook_bearer_token: str = ""
    lottery_dlt_auto_sync_enabled: bool = True
    lottery_dlt_sync_cron: str = "30 22 * * *"
    lottery_dlt_sync_page_size: int = Field(default=100, ge=1, le=500)
    lottery_dlt_sync_timeout_seconds: int = Field(default=30, ge=5, le=120)
    lottery_dlt_fallback_enabled: bool = True
    lottery_dlt_notify_enabled: bool = True
    lottery_dlt_notify_channel: str = "all"
    lottery_dlt_notify_on_no_changes: bool = False
    lottery_dlt_sporttery_url: str = (
        "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    )
    lottery_dlt_500_history_url: str = (
        "https://datachart.500.com/dlt/history/newinc/history.php"
    )
    fund_nav_sync_timeout_seconds: int = Field(default=20, ge=5, le=120)
    fund_nav_sync_max_workers: int = Field(default=4, ge=1, le=10)
    fund_nav_auto_sync_enabled: bool = True
    fund_nav_sync_cron: str = "0 19-22 * * 0-4"
    fund_nav_history_auto_sync_enabled: bool = True
    fund_nav_history_sync_limit: int = Field(default=365, ge=60, le=500)
    fund_nav_notify_enabled: bool = True
    fund_nav_notify_channel: str = Field(
        default="bark",
        pattern=r"^(all|bark|wecom|whatsapp|custom_webhook)$",
    )
    fund_ttskill_sync_enabled: bool = False
    fund_ttskill_sync_token: str = Field(default="", min_length=0)
    fund_eastmoney_pingzhongdata_url: str = (
        "https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
    )
    fund_eastmoney_holdings_url: str = (
        "http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        "?type=jjcc&code={fund_code}&topline=10&year=&month="
    )
    fund_lookthrough_target_links_json: str = "[]"
    fund_ai_summary_enabled: bool = False
    fund_ai_summary_provider: str = Field(
        default="webhook",
        pattern=r"^(webhook|openai_compatible)$",
    )
    fund_ai_summary_webhook_url: str = ""
    fund_ai_summary_bearer_token: str = ""
    fund_ai_summary_api_url: str = ""
    fund_ai_summary_api_key: str = ""
    fund_ai_summary_model: str = ""
    fund_ai_summary_timeout_seconds: int = Field(default=30, ge=5, le=120)
    fund_ai_auto_summary_enabled: bool = False
    fund_ai_auto_summary_max_per_day: int = Field(default=1, ge=1, le=1)
    pve_enabled: bool = False
    pve_url: str = ""
    pve_api_token_id: str = ""
    pve_api_token_secret: str = ""
    pve_verify_ssl: bool = True
    pve_timeout_seconds: int = Field(default=10, ge=3, le=60)
    pve_tasks_limit: int = Field(default=50, ge=1, le=200)
    docker_enabled: bool = False
    docker_url: str = "http://docker-socket-proxy:2375"
    docker_timeout_seconds: int = Field(default=10, ge=3, le=60)
    docker_stats_limit: int = Field(default=20, ge=1, le=50)
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
