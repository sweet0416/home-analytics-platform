from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config.settings import Settings, get_settings
from app.core.database.session import get_db
from app.core.notification.schemas import NotificationTestResult
from app.core.time import utcnow
from app.plugins.fund.application.ai_summary import FundDailyAiSummaryService
from app.plugins.fund.application.notification import FundDailyNotificationService
from app.plugins.fund.application.services import FundService
from app.plugins.fund.domain.constants import (
    FUND_MODULES,
    FUND_PLUGIN_CODE,
    FUND_PLUGIN_VERSION,
)
from app.plugins.fund.infrastructure.ai_summary_openai import FundAiSummaryOpenAIProvider
from app.plugins.fund.infrastructure.ai_summary_webhook import FundAiSummaryWebhookProvider
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.interfaces.schemas import (
    FundAccountSnapshotRead,
    FundAiAutomationRunRead,
    FundAllocationRead,
    FundCashFlowPerformanceRead,
    FundDailyAiInputRead,
    FundDailyAiSummaryArchiveRead,
    FundDailyAiSummaryRead,
    FundDailyAiSummaryStatusRead,
    FundDailyInsightsRead,
    FundDailyPushRequest,
    FundDailyReportRead,
    FundDailySnapshotDetailRead,
    FundDailySnapshotHistoryRead,
    FundDailySnapshotRead,
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
    FundTtSkillTradesImport,
    FundTtSkillTradesImportRead,
    FundWatchlistCreate,
    FundWatchlistNavSyncRead,
    FundWatchlistRead,
    FundWatchlistSummaryRead,
    FundWatchlistUpdate,
)
from app.plugins.fund.jobs.scheduler import (
    get_fund_scheduler_status,
    run_fund_ai_automation_after_external_nav_sync,
)
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/fund")


def get_fund_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FundService:
    return FundService(FundRepository(db), settings=settings)


def get_fund_ai_summary_service(
    settings: Settings = Depends(get_settings),
) -> FundDailyAiSummaryService:
    provider = (
        FundAiSummaryOpenAIProvider(settings)
        if settings.fund_ai_summary_provider == "openai_compatible"
        else FundAiSummaryWebhookProvider(settings)
    )
    return FundDailyAiSummaryService(
        settings=settings,
        provider=provider,
    )


def require_ttskill_sync_token(
    x_hap_sync_token: Annotated[
        str | None,
        Header(alias="X-HAP-Sync-Token"),
    ] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    configured_token = settings.fund_ttskill_sync_token.strip()
    if not settings.fund_ttskill_sync_enabled or not configured_token:
        raise AppError(
            code=ErrorCode.fund_ttskill_sync_disabled,
            message="Tiantian Skills synchronization is disabled.",
            status_code=503,
        )
    if not x_hap_sync_token or not compare_digest(
        x_hap_sync_token,
        configured_token,
    ):
        raise AppError(
            code=ErrorCode.fund_ttskill_unauthorized,
            message="Tiantian Skills synchronization token is invalid.",
            status_code=401,
        )


@router.get("/status", response_model=ApiResponse[FundStatusRead])
def get_fund_status() -> ApiResponse[FundStatusRead]:
    return ok(
        FundStatusRead(
            plugin=FUND_PLUGIN_CODE,
            display_name="Fund",
            version=FUND_PLUGIN_VERSION,
            status="operational",
            description="基金插件已支持持仓、净值、组合风险、自动更新和日报推送。",
            modules=FUND_MODULES,
            data_source_status="configured",
            storage_status="storage_ready",
            next_step="AI 摘要自动化和独立 Bark 推送已就绪；下一步验证生产配置与定时执行。",
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


@router.get("/positions/export")
def export_fund_positions(
    service: FundService = Depends(get_fund_service),
) -> Response:
    return Response(
        content="\ufeff" + service.export_positions_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="hap-fund-positions.csv"',
        },
    )


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


@router.post(
    "/integrations/ttskill/base-infos",
    response_model=ApiResponse[FundNavRecordRead],
    dependencies=[Depends(require_ttskill_sync_token)],
)
def import_ttskill_base_infos(
    payload: dict[str, object],
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavRecordRead]:
    return ok(
        service.import_ttskill_base_infos(payload),
        message="Tiantian Skills fund snapshot imported.",
    )


@router.post(
    "/integrations/ttskill/nav-info",
    response_model=ApiResponse[FundNavRecordRead],
    dependencies=[Depends(require_ttskill_sync_token)],
)
def import_ttskill_nav_info(
    payload: dict[str, object],
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundNavRecordRead]:
    return ok(
        service.import_ttskill_nav_info(payload),
        message="Tiantian Skills NAV info imported.",
    )


@router.post(
    "/integrations/ttskill/nav-sync-complete",
    dependencies=[Depends(require_ttskill_sync_token)],
)
def complete_ttskill_nav_sync() -> ApiResponse[dict[str, object]]:
    return ok(run_fund_ai_automation_after_external_nav_sync())


@router.post(
    "/integrations/ttskill/holdings",
    response_model=ApiResponse[FundAccountSnapshotRead],
    dependencies=[Depends(require_ttskill_sync_token)],
)
def import_ttskill_account_holdings(
    payload: dict[str, object],
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundAccountSnapshotRead]:
    return ok(
        service.import_ttskill_account_holdings(payload),
        message="Tiantian Skills account holdings imported.",
    )


@router.get(
    "/integrations/ttskill/holdings/latest",
    response_model=ApiResponse[FundAccountSnapshotRead | None],
)
def get_latest_ttskill_account_holdings(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundAccountSnapshotRead | None]:
    return ok(service.get_latest_ttskill_account_holdings())


@router.get("/transactions", response_model=ApiResponse[list[FundTransactionRead]])
def list_fund_transactions(
    limit: int = Query(default=100, ge=1, le=500),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[list[FundTransactionRead]]:
    return ok(service.list_transactions(limit=limit))


@router.get("/transactions/export")
def export_fund_transactions(
    limit: int = Query(default=500, ge=1, le=500),
    service: FundService = Depends(get_fund_service),
) -> Response:
    return Response(
        content="\ufeff" + service.export_transactions_csv(limit=limit),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="hap-fund-transactions.csv"',
        },
    )


@router.post(
    "/integrations/ttskill/trades/preview",
    response_model=ApiResponse[FundTtSkillTradesImportRead],
    dependencies=[Depends(require_ttskill_sync_token)],
)
def preview_ttskill_trades(
    payload: FundTtSkillTradesImport,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundTtSkillTradesImportRead]:
    return ok(service.import_ttskill_trades(payload, dry_run=True))


@router.post(
    "/integrations/ttskill/trades/import",
    response_model=ApiResponse[FundTtSkillTradesImportRead],
    dependencies=[Depends(require_ttskill_sync_token)],
)
def import_ttskill_trades(
    payload: FundTtSkillTradesImport,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundTtSkillTradesImportRead]:
    return ok(service.import_ttskill_trades(payload, dry_run=False))


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


@router.get(
    "/reports/daily/insights",
    response_model=ApiResponse[FundDailyInsightsRead],
)
def get_fund_daily_report_insights(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDailyInsightsRead]:
    return ok(service.get_daily_report_insights())


@router.get(
    "/reports/daily/ai-input",
    response_model=ApiResponse[FundDailyAiInputRead],
)
def get_fund_daily_report_ai_input(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDailyAiInputRead]:
    return ok(service.get_daily_report_ai_input())


@router.get(
    "/reports/daily/ai-summary/status",
    response_model=ApiResponse[FundDailyAiSummaryStatusRead],
)
def get_fund_daily_ai_summary_status(
    ai_service: FundDailyAiSummaryService = Depends(get_fund_ai_summary_service),
) -> ApiResponse[FundDailyAiSummaryStatusRead]:
    return ok(ai_service.get_status())


@router.get(
    "/reports/daily/ai-automation/status",
    response_model=ApiResponse[FundAiAutomationRunRead | None],
)
def get_fund_daily_ai_automation_status(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundAiAutomationRunRead | None]:
    return ok(service.get_ai_automation_run())


@router.post(
    "/reports/daily/ai-summary",
    response_model=ApiResponse[FundDailyAiSummaryRead],
)
def generate_fund_daily_ai_summary(
    service: FundService = Depends(get_fund_service),
    ai_service: FundDailyAiSummaryService = Depends(get_fund_ai_summary_service),
) -> ApiResponse[FundDailyAiSummaryRead]:
    report = service.get_daily_report()
    summary = ai_service.generate(service.get_daily_report_ai_input())
    snapshot = service.save_daily_report_snapshot(report)
    service.save_daily_ai_summary(snapshot.id, summary)
    return ok(summary, message="fund daily AI summary generated")


@router.get(
    "/reports/daily/snapshots",
    response_model=ApiResponse[FundDailySnapshotHistoryRead],
)
def get_fund_daily_report_snapshots(
    limit: int = Query(default=30, ge=1, le=365),
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDailySnapshotHistoryRead]:
    return ok(service.get_daily_report_snapshot_history(limit=limit))


@router.get("/reports/daily/snapshots/export")
def export_fund_daily_report_snapshots(
    limit: int = Query(default=365, ge=1, le=365),
    service: FundService = Depends(get_fund_service),
) -> Response:
    return Response(
        content="\ufeff" + service.export_daily_report_snapshots_csv(limit=limit),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="hap-fund-daily-snapshots.csv"',
        },
    )


@router.get(
    "/reports/daily/snapshots/{snapshot_id}",
    response_model=ApiResponse[FundDailySnapshotDetailRead],
)
def get_fund_daily_report_snapshot_detail(
    snapshot_id: int,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDailySnapshotDetailRead]:
    return ok(service.get_daily_report_snapshot_detail(snapshot_id))


@router.get(
    "/reports/daily/snapshots/{snapshot_id}/ai-summary",
    response_model=ApiResponse[FundDailyAiSummaryArchiveRead],
)
def get_fund_daily_report_snapshot_ai_summary(
    snapshot_id: int,
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDailyAiSummaryArchiveRead]:
    summary = service.get_daily_ai_summary(snapshot_id)
    if summary is None:
        raise AppError(
            code=ErrorCode.not_found,
            message="Fund daily AI summary was not found.",
            status_code=404,
        )
    return ok(summary)


@router.post(
    "/reports/daily/snapshots",
    response_model=ApiResponse[FundDailySnapshotRead],
)
def save_fund_daily_report_snapshot(
    service: FundService = Depends(get_fund_service),
) -> ApiResponse[FundDailySnapshotRead]:
    return ok(
        service.save_daily_report_snapshot(),
        message="fund daily report snapshot saved",
    )


@router.post(
    "/reports/daily/push",
    response_model=ApiResponse[NotificationTestResult],
)
def push_fund_daily_report(
    payload: FundDailyPushRequest,
    service: FundService = Depends(get_fund_service),
    settings: Settings = Depends(get_settings),
) -> ApiResponse[NotificationTestResult]:
    report = service.get_daily_report()
    snapshot = service.save_daily_report_snapshot(report)
    insights = service.get_daily_report_insights()
    ai_summary = (
        service.get_daily_ai_summary(snapshot.id)
        if payload.include_ai_summary
        else None
    )
    result = FundDailyNotificationService(settings=settings).send(
        report=report,
        channel=payload.channel,
        snapshot=snapshot,
        insights=insights,
        ai_summary=ai_summary,
    )
    if payload.include_ai_summary:
        run = service.repository.get_ai_automation_run(report_date=snapshot.report_date)
        if run is not None:
            sent = any(item.status == "sent" for item in result.results)
            run.push_status = "SUCCESS" if sent else "FAILED"
            run.push_error_message = "" if sent else "; ".join(
                item.message for item in result.results
            )
            run.updated_at = utcnow()
            service.repository.commit()
    return ok(result, message="fund daily report push finished")
