from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.backup.scheduler import start_backup_scheduler, stop_backup_scheduler
from app.core.config.settings import get_settings
from app.core.database.session import create_database_schema
from app.core.logging.setup import configure_logging
from app.core.middleware import add_trace_id_middleware
from app.core.plugins.registry import plugin_registry
from app.plugins.lottery.plugin import lottery_plugin
from app.shared.exceptions.handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    create_database_schema()
    start_backup_scheduler()
    plugin_registry.register(lottery_plugin)
    try:
        yield
    finally:
        stop_backup_scheduler()
        plugin_registry.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.middleware("http")(add_trace_id_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
