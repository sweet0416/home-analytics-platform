from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config.settings import Settings, get_settings
from app.core.database.session import get_db
from app.core.notification.schemas import NotificationTestResult
from app.plugins.fund.application.notification import FundDailyNotificationService
from app.plugins.fund.application.services import FundService
from app.plugins.fund.domain.constants import FUND_MODULES, FUND_PLUGIN_CODE
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.interfaces.schemas import (
    FundAllocationRead,
    FundCashFlowPerformanceRead,
    FundDailyPushRequest,
    FundDailyReportRead,
    FundDisclosureSyncRead,
    FundHoldingCorrelationRead,
    FundHoldingHistorySyncRead,
    FundHoldingHistorySyncRequest,
    FundHoldingRiskRead,
    FundHoldingSummaryRead,
    FundLatestNavRead,
    FundLookthroughRead,
    FundNavFreshnessRead,
    FundNavHistorySyncRead,
    FundNavHistorySyncRequest,
    FundNavRecordCreate,
    FundNavRecordRead,
    FundNavRiskRead,
    FundNavSchedulerStatusRead,
    FundNavSummaryRead,
    FundNavSyncLatestRequest,
    FundPortfolioBenchmarkRead,
    FundPortfolioPerformanceRead,
    FundPositionCreate,
    FundPositionRead,
    FundPositionUpdate,
    FundProfileSyncRead,
    FundRiskContributionRead,
    FundStatusRead,
    FundTargetLinkCreate,
    FundTargetLinkRead,
    FundTransactionCreate,
    FundTransactionRead,
    FundTransactionSummaryRead,
    FundWatchlistCreate,
    FundWatchlistNavSyncRead,
    FundWatchlistRead,
    FundWatchlistSummaryRead,
    FundWatchlistUpdate,
)
from app.plugins.fund.jobs.scheduler import get_fund_scheduler_status
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/fund")


def get_fund_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FundService:
    return FundService(FundRepository(db), settings=settings)


@router.get("/status", response_model=ApiResponse[FundStatusRead])
def get_fund_status() -> ApiResponse[FundStatusRead]:
    return ok(
        FundStatusRead(
            plugin=FUND_PLUGIN_CODE,
            display_name="Fund",
            version="0.6.0",
            status="operational",
            description="基金插件已支持持仓、净值、组合风险、自动更新和日报推送。",
            modules=FUND_MODULES,
            data_source_status="configured",
            storage_status="storage_ready",
            next_step="下一步完善结构化日报摘要，为后续 AI 总结接入准备稳定数据契约。",
        )
    )


@router.get(
    "/nav-scheduler/status",
    response_model=ApiResponse[FundNavSchedulerStatusRead],
)
def get_fund_nav_scheduler_status() -> ApiResponse[FundNavSchedulerStatusRead]:
    return ok(FundNavSchedulerStatusRead.model_validate(get_fund_scheduler_status()))


@router.get("/positions", response_model=ApiResponse[list[FundPositionRead]])
def list_fund_positions(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundPositionRead]]:
    return ok(service.list_positions())


@router.get(
    "/holdings/nav-freshness",
    response_model=ApiResponse[FundNavFreshnessRead],
)
def get_fund_nav_freshness(
    stale_after_business_days: int = Query(default=2, ge=1, le=10),
    qdii_stale_after_business_days: int = Query(default=4, ge=1, le=10),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavFreshnessRead]:
    return ok(
        service.get_nav_freshness(
            stale_after_business_days=stale_after_business_days,
            qdii_stale_after_business_days=qdii_stale_after_business_days,
        )
    )


@router.post(
    "/holdings/sync-profiles",
    response_model=ApiResponse[FundProfileSyncRead],
)
def sync_held_fund_profiles(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundProfileSyncRead]:
    return ok(service.sync_held_fund_profiles())


@router.get("/transactions", response_model=ApiResponse[list[FundTransactionRead]])
def list_fund_transactions(
    limit: int = Query(default=100, ge=1, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundTransactionRead]]:
    return ok(service.list_transactions(limit=limit))


@router.post("/transactions", response_model=ApiResponse[FundTransactionRead])
def create_fund_transaction(
    payload: FundTransactionCreate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundTransactionRead]:
    return ok(service.create_transaction(payload))


@router.get(
    "/transactions/summary",
    response_model=ApiResponse[FundTransactionSummaryRead],
)
def get_fund_transaction_summary(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundTransactionSummaryRead]:
    return ok(service.get_transaction_summary())


@router.get(
    "/performance/cash-flow",
    response_model=ApiResponse[FundCashFlowPerformanceRead],
)
def get_fund_cash_flow_performance(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundCashFlowPerformanceRead]:
    return ok(service.get_cash_flow_performance())


@router.delete(
    "/transactions/{transaction_id}",
    response_model=ApiResponse[dict[str, object]],
)
def delete_fund_transaction(
    transaction_id: int,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[dict[str, object]]:
    service.delete_transaction(transaction_id)
    return ok({"deleted": True, "id": transaction_id})


@router.get("/watchlist", response_model=ApiResponse[list[FundWatchlistRead]])
def list_fund_watchlist(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundWatchlistRead]]:
    return ok(service.list_watchlist_items())


@router.post("/watchlist", response_model=ApiResponse[FundWatchlistRead])
def create_fund_watchlist_item(
    payload: FundWatchlistCreate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundWatchlistRead]:
    return ok(service.create_watchlist_item(payload))


@router.get("/watchlist/summary", response_model=ApiResponse[FundWatchlistSummaryRead])
def get_fund_watchlist_summary(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundWatchlistSummaryRead]:
    return ok(service.get_watchlist_summary())


@router.post("/watchlist/sync-nav", response_model=ApiResponse[FundWatchlistNavSyncRead])
def sync_fund_watchlist_navs(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundWatchlistNavSyncRead]:
    return ok(service.sync_watchlist_navs())


@router.get("/nav-records", response_model=ApiResponse[list[FundNavRecordRead]])
def list_fund_nav_records(
    limit: int = 50,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundNavRecordRead]]:
    return ok(service.list_nav_records(limit=limit))


@router.post("/nav-records", response_model=ApiResponse[FundNavRecordRead])
def create_fund_nav_record(
    payload: FundNavRecordCreate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavRecordRead]:
    return ok(service.create_nav_record(payload))


@router.post("/nav-records/sync-latest", response_model=ApiResponse[FundNavRecordRead])
def sync_latest_fund_nav_record(
    payload: FundNavSyncLatestRequest,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavRecordRead]:
    return ok(service.sync_latest_nav(payload))


@router.post("/nav-records/sync-history", response_model=ApiResponse[FundNavHistorySyncRead])
def sync_fund_nav_history(
    payload: FundNavHistorySyncRequest,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavHistorySyncRead]:
    return ok(service.sync_nav_history(payload))


@router.get("/nav-records/history", response_model=ApiResponse[list[FundNavRecordRead]])
def get_fund_nav_history(
    fund_code: str,
    limit: int = Query(default=365, ge=2, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundNavRecordRead]]:
    return ok(service.list_nav_history(fund_code=fund_code, limit=limit))


@router.get("/nav-records/risk", response_model=ApiResponse[FundNavRiskRead])
def get_fund_nav_risk(
    fund_code: str,
    limit: int = Query(default=365, ge=2, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavRiskRead]:
    return ok(service.get_nav_risk(fund_code=fund_code, limit=limit))


@router.post("/lookup/latest-nav", response_model=ApiResponse[FundLatestNavRead])
def lookup_latest_fund_nav(
    payload: FundNavSyncLatestRequest,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundLatestNavRead]:
    return ok(service.lookup_latest_nav(payload))


@router.get("/nav-records/summary", response_model=ApiResponse[FundNavSummaryRead])
def get_fund_nav_summary(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavSummaryRead]:
    return ok(service.get_nav_summary())


@router.delete("/nav-records/{record_id}", response_model=ApiResponse[dict[str, object]])
def delete_fund_nav_record(
    record_id: int,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[dict[str, object]]:
    service.delete_nav_record(record_id)
    return ok({"deleted": True, "id": record_id})


@router.put("/watchlist/{item_id}", response_model=ApiResponse[FundWatchlistRead])
def update_fund_watchlist_item(
    item_id: int,
    payload: FundWatchlistUpdate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundWatchlistRead]:
    return ok(service.update_watchlist_item(item_id, payload))


@router.delete("/watchlist/{item_id}", response_model=ApiResponse[dict[str, object]])
def delete_fund_watchlist_item(
    item_id: int,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[dict[str, object]]:
    service.delete_watchlist_item(item_id)
    return ok({"deleted": True, "id": item_id})


@router.post("/positions", response_model=ApiResponse[FundPositionRead])
def create_fund_position(
    payload: FundPositionCreate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundPositionRead]:
    return ok(service.create_position(payload))


@router.put("/positions/{position_id}", response_model=ApiResponse[FundPositionRead])
def update_fund_position(
    position_id: int,
    payload: FundPositionUpdate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundPositionRead]:
    return ok(service.update_position(position_id, payload))


@router.delete("/positions/{position_id}", response_model=ApiResponse[dict[str, object]])
def delete_fund_position(
    position_id: int,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[dict[str, object]]:
    service.delete_position(position_id)
    return ok({"deleted": True, "id": position_id})


@router.get("/holdings/summary", response_model=ApiResponse[FundHoldingSummaryRead])
def get_fund_holding_summary(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundHoldingSummaryRead]:
    return ok(service.get_holding_summary())


@router.get("/holdings/allocation", response_model=ApiResponse[FundAllocationRead])
def get_fund_allocation(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundAllocationRead]:
    return ok(service.get_allocation())


@router.get("/holdings/risk", response_model=ApiResponse[FundHoldingRiskRead])
def get_fund_holding_risk(
    limit: int = Query(default=365, ge=2, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundHoldingRiskRead]:
    return ok(service.get_holding_risk(limit=limit))


@router.get(
    "/holdings/performance",
    response_model=ApiResponse[FundPortfolioPerformanceRead],
)
def get_fund_portfolio_performance(
    limit: int = Query(default=365, ge=2, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundPortfolioPerformanceRead]:
    return ok(service.get_portfolio_performance(limit=limit))


@router.get(
    "/holdings/benchmark",
    response_model=ApiResponse[FundPortfolioBenchmarkRead],
)
def get_fund_portfolio_benchmark(
    benchmark_code: str = Query(min_length=1, max_length=16),
    limit: int = Query(default=365, ge=3, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundPortfolioBenchmarkRead]:
    return ok(
        service.get_portfolio_benchmark(
            benchmark_code=benchmark_code,
            limit=limit,
        )
    )


@router.get(
    "/holdings/correlation",
    response_model=ApiResponse[FundHoldingCorrelationRead],
)
def get_fund_holding_correlation(
    limit: int = Query(default=365, ge=3, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundHoldingCorrelationRead]:
    return ok(service.get_holding_correlation(limit=limit))


@router.get(
    "/holdings/risk-contribution",
    response_model=ApiResponse[FundRiskContributionRead],
)
def get_fund_risk_contribution(
    limit: int = Query(default=365, ge=3, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundRiskContributionRead]:
    return ok(service.get_risk_contribution(limit=limit))


@router.get(
    "/holdings/lookthrough",
    response_model=ApiResponse[FundLookthroughRead],
)
def get_fund_lookthrough(
    stale_after_days: int = Query(default=180, ge=30, le=730),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundLookthroughRead]:
    return ok(service.get_lookthrough(stale_after_days=stale_after_days))


@router.post(
    "/holdings/lookthrough/sync",
    response_model=ApiResponse[FundDisclosureSyncRead],
)
def sync_fund_lookthrough(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDisclosureSyncRead]:
    return ok(service.sync_holding_disclosures())


@router.get(
    "/holdings/lookthrough/target-links",
    response_model=ApiResponse[list[FundTargetLinkRead]],
)
def list_fund_target_links(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundTargetLinkRead]]:
    return ok(service.list_target_links())


@router.post(
    "/holdings/lookthrough/target-links",
    response_model=ApiResponse[FundTargetLinkRead],
)
def save_fund_target_link(
    payload: FundTargetLinkCreate,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundTargetLinkRead]:
    return ok(service.save_target_link(payload))


@router.delete(
    "/holdings/lookthrough/target-links/{parent_fund_code}",
    response_model=ApiResponse[dict[str, object]],
)
def delete_fund_target_link(
    parent_fund_code: str,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[dict[str, object]]:
    return ok(service.delete_target_link(parent_fund_code))


@router.post(
    "/holdings/sync-history",
    response_model=ApiResponse[FundHoldingHistorySyncRead],
)
def sync_fund_holding_history(
    payload: FundHoldingHistorySyncRequest,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundHoldingHistorySyncRead]:
    return ok(service.sync_holding_history(limit=payload.limit))


@router.get("/reports/daily", response_model=ApiResponse[FundDailyReportRead])
def get_fund_daily_report(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDailyReportRead]:
    return ok(service.get_daily_report())


@router.post(
    "/reports/daily/push",
    response_model=ApiResponse[NotificationTestResult],
)
def push_fund_daily_report(
    payload: FundDailyPushRequest,
    service: FundService = Depends(get_fund_service),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[NotificationTestResult]:
    result = FundDailyNotificationService(settings=settings).send(
        report=service.get_daily_report(),
        channel=payload.channel,
    )
    return ok(result, message="fund daily report push finished")
