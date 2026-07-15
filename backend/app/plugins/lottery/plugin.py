from app.core.database.session import SessionLocal
from app.core.plugins.contracts import PluginManifest
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository
from app.plugins.lottery.interfaces.router import router
from app.plugins.lottery.jobs.scheduler import start_lottery_scheduler, stop_lottery_scheduler


def seed_lottery_data() -> None:
    db = SessionLocal()
    try:
        LotteryRepository(db).ensure_dlt_seed_data()
    finally:
        db.close()


lottery_plugin = PluginManifest(
    name="lottery",
    display_name="Lottery",
    version="1.1.0",
    description="Lottery analysis plugin with DLT draw sync support.",
    routes=[router],
    menu_items=[
        {"name": "lottery-overview", "label": "大乐透", "path": "/lottery/dlt"},
    ],
    startup_hooks=[seed_lottery_data, start_lottery_scheduler],
    shutdown_hooks=[stop_lottery_scheduler],
)
