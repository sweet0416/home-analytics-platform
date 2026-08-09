from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from app.core.config.settings import Settings, get_settings
from app.plugins.docker.application.service import DockerService
from app.plugins.docker.infrastructure.docker_api import DockerApiError
from app.plugins.docker.interfaces.schemas import DockerResourceRead, DockerStatusRead
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/docker")


def get_docker_service(settings: Settings = Depends(get_settings)) -> DockerService:
    return DockerService(settings)


def _read(service_call: Callable[[], list[dict[str, Any]]]) -> ApiResponse[DockerResourceRead]:
    try:
        data = service_call()
    except DockerApiError as exc:
        code = ErrorCode.docker_not_configured if "not configured" in str(exc) else ErrorCode.docker_api_unavailable
        raise AppError(code=code, message=str(exc), status_code=503) from exc
    return ok(DockerResourceRead(data=data))


@router.get("/status", response_model=ApiResponse[DockerStatusRead])
def get_docker_status(service: DockerService = Depends(get_docker_service)) -> ApiResponse[DockerStatusRead]:
    return ok(DockerStatusRead.model_validate(service.status()))


@router.get("/containers", response_model=ApiResponse[DockerResourceRead])
def get_docker_containers(service: DockerService = Depends(get_docker_service)) -> ApiResponse[DockerResourceRead]:
    return _read(service.containers)


@router.get("/images", response_model=ApiResponse[DockerResourceRead])
def get_docker_images(service: DockerService = Depends(get_docker_service)) -> ApiResponse[DockerResourceRead]:
    return _read(service.images)


@router.get("/volumes", response_model=ApiResponse[DockerResourceRead])
def get_docker_volumes(service: DockerService = Depends(get_docker_service)) -> ApiResponse[DockerResourceRead]:
    return _read(service.volumes)
