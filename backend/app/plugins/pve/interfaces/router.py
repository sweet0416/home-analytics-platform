from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from app.core.config.settings import Settings, get_settings
from app.plugins.pve.application.service import PveService
from app.plugins.pve.infrastructure.proxmox_api import ProxmoxApiError
from app.plugins.pve.interfaces.schemas import PveResourceRead, PveStatusRead
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/pve")


def get_pve_service(settings: Settings = Depends(get_settings)) -> PveService:
    return PveService(settings)


def _read(
    service_call: Callable[[], list[dict[str, Any]]],
) -> ApiResponse[PveResourceRead]:
    try:
        data = service_call()
    except ProxmoxApiError as exc:
        code = ErrorCode.pve_not_configured if "not configured" in str(exc) else ErrorCode.pve_api_unavailable
        raise AppError(code=code, message=str(exc), status_code=503) from exc
    return ok(PveResourceRead(data=data))


@router.get("/status", response_model=ApiResponse[PveStatusRead])
def get_pve_status(service: PveService = Depends(get_pve_service)) -> ApiResponse[PveStatusRead]:
    return ok(PveStatusRead.model_validate(service.status()))


@router.get("/nodes", response_model=ApiResponse[PveResourceRead])
def get_pve_nodes(service: PveService = Depends(get_pve_service)) -> ApiResponse[PveResourceRead]:
    return _read(service.nodes)


@router.get("/guests", response_model=ApiResponse[PveResourceRead])
def get_pve_guests(service: PveService = Depends(get_pve_service)) -> ApiResponse[PveResourceRead]:
    return _read(service.guests)


@router.get("/storage", response_model=ApiResponse[PveResourceRead])
def get_pve_storage(service: PveService = Depends(get_pve_service)) -> ApiResponse[PveResourceRead]:
    return _read(service.storage)


@router.get("/tasks", response_model=ApiResponse[PveResourceRead])
def get_pve_tasks(service: PveService = Depends(get_pve_service)) -> ApiResponse[PveResourceRead]:
    return _read(service.tasks)
