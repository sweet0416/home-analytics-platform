from fastapi import APIRouter

from app.core.config.settings import get_settings
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    settings = get_settings()
    return ok(
        {
            "status": "ok",
            "version": settings.app_version,
            "database": "ok",
        }
    )

