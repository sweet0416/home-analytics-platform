from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database.session import get_db
from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.constants import DLT_DISCLAIMER
from app.plugins.lottery.domain.sync import DrawSyncCommand
from app.plugins.lottery.interfaces.schemas import (
    DisclaimerRead,
    LotteryDrawPageRead,
    LotteryDrawRead,
    LotteryRuleRead,
    LotterySyncRequest,
    LotterySyncRunPageRead,
    LotterySyncRunRead,
)
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/dlt")


@router.get("/rules/current", response_model=ApiResponse[LotteryRuleRead])
def get_current_rule(db: Session = Depends(get_db)) -> ApiResponse[LotteryRuleRead]:
    service = LotteryService(db)
    return ok(service.get_current_rule())


@router.get("/draws", response_model=ApiResponse[LotteryDrawPageRead])
def list_draws(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ApiResponse[LotteryDrawPageRead]:
    service = LotteryService(db)
    return ok(service.list_draws(page=page, page_size=page_size))


@router.get("/draws/latest", response_model=ApiResponse[LotteryDrawRead])
def get_latest_draw(db: Session = Depends(get_db)) -> ApiResponse[LotteryDrawRead]:
    service = LotteryService(db)
    return ok(service.get_latest_draw())


@router.get("/draws/{issue_no}", response_model=ApiResponse[LotteryDrawRead])
def get_draw_by_issue(issue_no: str, db: Session = Depends(get_db)) -> ApiResponse[LotteryDrawRead]:
    service = LotteryService(db)
    return ok(service.get_draw_by_issue(issue_no))


@router.post("/sync", response_model=ApiResponse[LotterySyncRunRead])
def sync_draws(
    payload: LotterySyncRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySyncRunRead]:
    service = LotteryService(db)
    command = DrawSyncCommand(
        sync_type=payload.sync_type,
        page=payload.page,
        page_size=payload.page_size,
        force=payload.force,
    )
    return ok(service.sync_draws(command))


@router.get("/sync/latest", response_model=ApiResponse[LotterySyncRunRead])
def get_latest_sync_run(db: Session = Depends(get_db)) -> ApiResponse[LotterySyncRunRead]:
    service = LotteryService(db)
    return ok(service.get_latest_sync_run())


@router.get("/sync/runs", response_model=ApiResponse[LotterySyncRunPageRead])
def list_sync_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, pattern="^(running|success|partial_success|failed)$"),
    sync_type: str | None = Query(default=None, pattern="^(manual|scheduled|backfill)$"),
    db: Session = Depends(get_db),
) -> ApiResponse[LotterySyncRunPageRead]:
    service = LotteryService(db)
    return ok(
        service.list_sync_runs(
            page=page,
            page_size=page_size,
            status=status,
            sync_type=sync_type,
        )
    )


@router.get("/disclaimer", response_model=ApiResponse[DisclaimerRead])
def get_disclaimer() -> ApiResponse[DisclaimerRead]:
    return ok({"disclaimer": DLT_DISCLAIMER})
