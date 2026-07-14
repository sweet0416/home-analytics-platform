import sys

from loguru import logger

from app.core.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
    logger.add(
        settings.log_dir / "hap.log",
        level=settings.log_level,
        rotation="10 MB",
        retention="14 days",
        enqueue=True,
    )

