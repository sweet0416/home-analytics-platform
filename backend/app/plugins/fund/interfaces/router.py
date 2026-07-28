from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.plugins.fund.domain.constants import FUND_MODULES, FUND_PLUGIN_CODE
from app.core.database.session import get_db
from app.plugins.fund.application.services import FundService
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.interfaces.schemas import (
    FundHoldingSummaryRead,
    FundPositionCreate,
    FundPositionRead,
    FundStatusRead,
)
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/fund")


def get_fund_service(db: Session = Depends(get_db)) -> FundService:
    return FundService(FundRepository(db))


@router.get("/status", response_model=ApiResponse[FundStatusRead])
def get_fund_status() -> ApiResponse[FundStatusRead]:
    return ok(
        FundStatusRead(
            plugin=FUND_PLUGIN_CODE,
            display_name="Fund",
            version="0.1.0",
            status="scaffolded",
            description="基金分析插件已接入 HAP 插件体系，已支持手动录入基金持仓。",
            modules=FUND_MODULES,
            data_source_status="not_configured",
            storage_status="created",
            next_step="下一步接入基金净值数据源，并基于持仓计算收益曲线、回撤和日报。",
        )
    )


@router.get("/positions", response_model=ApiResponse[list[FundPositionRead]])
def list_fund_positions(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundPositionRead]]:
    return ok(service.list_positions())


@router.post("/positions", response_model=ApiResponse[FundPositionRead])
def create_fund_position(
    payload: FundPositionCreate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundPositionRead]:
    return ok(service.create_position(payload))


@router.get("/holdings/summary", response_model=ApiResponse[FundHoldingSummaryRead])
def get_fund_holding_summary(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundHoldingSummaryRead]:
    return ok(service.get_holding_summary())
