import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import Literal
from zoneinfo import ZoneInfo

from loguru import logger

from app.core.config.settings import Settings
from app.core.time import utcnow
from app.plugins.fund.domain.daily_insights import (
    DailyInsightSnapshot,
    calculate_daily_insights,
)
from app.plugins.fund.domain.holding_correlation import (
    FundCorrelationSeries,
    calculate_holding_correlations,
)
from app.plugins.fund.domain.lookthrough import (
    LookthroughFundDisclosure,
    LookthroughHolding,
    calculate_lookthrough,
)
from app.plugins.fund.domain.nav_freshness import count_business_days_since
from app.plugins.fund.domain.nav_risk import calculate_nav_risk
from app.plugins.fund.domain.portfolio_benchmark import (
    calculate_portfolio_benchmark,
)
from app.plugins.fund.domain.portfolio_performance import (
    PortfolioFundSeries,
    calculate_static_portfolio_performance,
)
from app.plugins.fund.domain.risk_contribution import (
    FundRiskContributionSeries,
    calculate_risk_contributions,
)
from app.plugins.fund.domain.target_links import (
    TargetFundLink,
    parse_target_fund_links,
)
from app.plugins.fund.infrastructure.persistence.models import (
    FundAccountSnapshotModel,
    FundDailyReportSnapshotModel,
    FundDisclosureModel,
    FundModel,
    FundNavRecordModel,
    FundPositionModel,
    FundTargetLinkModel,
    FundTransactionModel,
    FundWatchlistItemModel,
)
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.infrastructure.sources.eastmoney import (
    EastmoneyFundNavSource,
    FundLatestNav,
)
from app.plugins.fund.infrastructure.sources.eastmoney_holdings import (
    EastmoneyFundHoldingsSource,
    FundHoldingsDisclosure,
)
from app.plugins.fund.infrastructure.sources.ttskill import (
    TtSkillAccountHoldingSource,
    TtSkillBaseInfoSource,
)
from app.plugins.fund.infrastructure.sources.ttskill_nav import TtSkillNavInfoSource
from app.plugins.fund.infrastructure.sources.ttskill_trades import (
    TtSkillTrade,
    TtSkillTradeQuerySource,
)
from app.plugins.fund.interfaces.schemas import (
    FundAccountHoldingRead,
    FundAccountManualOnlyRead,
    FundAccountSnapshotRead,
    FundAiAutomationRunRead,
    FundAllocationGroupRead,
    FundAllocationHoldingRead,
    FundAllocationRead,
    FundCashFlowPerformanceRead,
    FundCorrelationMemberRead,
    FundCorrelationPairRead,
    FundDailyAiInputRead,
    FundDailyAiSummaryArchiveRead,
    FundDailyAiSummaryRead,
    FundDailyAlertRead,
    FundDailyAnalysisContextRead,
    FundDailyDataQualityRead,
    FundDailyFactRead,
    FundDailyInsightAlertRead,
    FundDailyInsightsRead,
    FundDailyPeriodComparisonRead,
    FundDailyReportRead,
    FundDailySnapshotChangeRead,
    FundDailySnapshotDetailRead,
    FundDailySnapshotHistoryRead,
    FundDailySnapshotRead,
    FundDisclosureSyncItemRead,
    FundDisclosureSyncRead,
    FundHoldingCorrelationRead,
    FundHoldingHistorySyncItemRead,
    FundHoldingHistorySyncRead,
    FundHoldingRiskItemRead,
    FundHoldingRiskRead,
    FundHoldingSummaryRead,
    FundLatestNavRead,
    FundLookthroughAssetRead,
    FundLookthroughRead,
    FundLookthroughSnapshotRead,
    FundNavFreshnessItemRead,
    FundNavFreshnessRead,
    FundNavHistorySyncRead,
    FundNavHistorySyncRequest,
    FundNavRecordCreate,
    FundNavRecordRead,
    FundNavRiskRead,
    FundNavSummaryRead,
    FundNavSyncLatestRequest,
    FundPortfolioBenchmarkPointRead,
    FundPortfolioBenchmarkRead,
    FundPortfolioMemberRead,
    FundPortfolioPerformancePointRead,
    FundPortfolioPerformanceRead,
    FundPositionCreate,
    FundPositionRead,
    FundPositionUpdate,
    FundProfileSyncItemRead,
    FundProfileSyncRead,
    FundRiskContributionItemRead,
    FundRiskContributionRead,
    FundTargetLinkCreate,
    FundTargetLinkRead,
    FundTrackedNavSyncRead,
    FundTransactionCreate,
    FundTransactionRead,
    FundTransactionSummaryRead,
    FundTtSkillTradeImportItemRead,
    FundTtSkillTradesImport,
    FundTtSkillTradesImportRead,
    FundWatchlistCreate,
    FundWatchlistNavSyncItemRead,
    FundWatchlistNavSyncRead,
    FundWatchlistRead,
    FundWatchlistSummaryRead,
    FundWatchlistUpdate,
)
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class FundService:
    def __init__(
        self,
        repository: FundRepository,
        settings: Settings | None = None,
        nav_source: EastmoneyFundNavSource | None = None,
        holdings_source: EastmoneyFundHoldingsSource | None = None,
        target_links: list[TargetFundLink] | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.nav_source = nav_source
        self.holdings_source = holdings_source
        self._target_links_override = target_links
        self._environment_target_links = (
            []
            if target_links is not None
            else parse_target_fund_links(
                settings.fund_lookthrough_target_links_json
                if settings is not None
                else "[]"
            )
        )

    def _effective_target_links(self) -> list[TargetFundLink]:
        if self._target_links_override is not None:
            return self._target_links_override

        links_by_parent = {
            link.parent_fund_code: link
            for link in self._environment_target_links
        }
        for record in self.repository.list_target_links():
            if not record.enabled:
                links_by_parent.pop(record.parent_fund_code, None)
                continue
            links_by_parent[record.parent_fund_code] = self._to_target_link(record)
        return [links_by_parent[code] for code in sorted(links_by_parent)]

    def list_target_links(self) -> list[FundTargetLinkRead]:
        database_records = {
            record.parent_fund_code: record
            for record in self.repository.list_target_links()
        }
        result: list[FundTargetLinkRead] = []
        for link in self._effective_target_links():
            record = database_records.get(link.parent_fund_code)
            result.append(
                self._to_target_link_read(
                    link,
                    origin=(
                        "database"
                        if record is not None and record.enabled
                        else "environment"
                    ),
                )
            )
        return result

    def save_target_link(
        self,
        payload: FundTargetLinkCreate,
    ) -> FundTargetLinkRead:
        record = self.repository.upsert_target_link(
            parent_fund_code=payload.parent_fund_code,
            target_fund_code=payload.target_fund_code,
            target_fund_name=payload.target_fund_name,
            target_allocation_ratio=payload.target_allocation_ratio,
            report_date=payload.report_date,
            source_url=payload.source_url,
        )
        self.repository.commit()
        return self._to_target_link_read(
            self._to_target_link(record),
            origin="database",
        )

    def delete_target_link(self, parent_fund_code: str) -> dict[str, object]:
        normalized_code = parent_fund_code.strip()
        record = self.repository.get_target_link(normalized_code)
        if record is None:
            environment_link = next(
                (
                    link
                    for link in self._environment_target_links
                    if link.parent_fund_code == normalized_code
                ),
                None,
            )
            if environment_link is None:
                raise AppError(
                    code=ErrorCode.not_found,
                    message="Target ETF relationship was not found.",
                    status_code=404,
                )
            record = self.repository.upsert_target_link(
                parent_fund_code=environment_link.parent_fund_code,
                target_fund_code=environment_link.target_fund_code,
                target_fund_name=environment_link.target_fund_name,
                target_allocation_ratio=environment_link.target_allocation_ratio,
                report_date=environment_link.report_date,
                source_url=environment_link.source_url,
            )
        self.repository.disable_target_link(record)
        self.repository.commit()
        return {"deleted": True, "parent_fund_code": normalized_code}

    def list_positions(self) -> list[FundPositionRead]:
        return [self._to_position_read(position) for position in self.repository.list_positions()]

    def get_nav_freshness(
        self,
        stale_after_business_days: int = 2,
        qdii_stale_after_business_days: int = 4,
        as_of_date: date | None = None,
    ) -> FundNavFreshnessRead:
        observation_date = as_of_date or datetime.now(
            ZoneInfo("Asia/Shanghai")
        ).date()
        positions = self.repository.list_positions()
        fund_ids = sorted({position.fund_id for position in positions})
        latest_by_fund_id = {
            record.fund_id: record
            for record in self.repository.list_latest_nav_records_for_fund_ids(
                fund_ids
            )
        }
        positions_by_fund_id: dict[int, list[FundPositionModel]] = {}
        for position in positions:
            positions_by_fund_id.setdefault(position.fund_id, []).append(position)

        items: list[FundNavFreshnessItemRead] = []
        for fund_id in fund_ids:
            fund_positions = positions_by_fund_id[fund_id]
            fund = fund_positions[0].fund
            latest = latest_by_fund_id.get(fund_id)
            is_qdii = any(
                "QDII" in value.upper()
                for value in (fund.fund_type, fund.name)
            )
            allowed_business_days = (
                qdii_stale_after_business_days
                if is_qdii
                else stale_after_business_days
            )
            if latest is None:
                age = None
                status = "missing"
            else:
                age = count_business_days_since(
                    latest.nav_date,
                    observation_date,
                )
                status = (
                    "fresh"
                    if age <= allowed_business_days
                    else "stale"
                )
            items.append(
                FundNavFreshnessItemRead(
                    fund_code=fund.code,
                    fund_name=fund.name,
                    fund_type=fund.fund_type,
                    account_names=sorted(
                        {position.account_name for position in fund_positions}
                    ),
                    latest_nav_date=latest.nav_date if latest else None,
                    business_day_age=age,
                    allowed_business_days=allowed_business_days,
                    source=latest.source if latest else None,
                    status=status,
                )
            )

        dated_items = [
            item.latest_nav_date
            for item in items
            if item.latest_nav_date is not None
        ]
        return FundNavFreshnessRead(
            as_of_date=observation_date,
            stale_after_business_days=stale_after_business_days,
            qdii_stale_after_business_days=qdii_stale_after_business_days,
            position_count=len(positions),
            fund_count=len(items),
            fresh_count=sum(item.status == "fresh" for item in items),
            stale_count=sum(item.status == "stale" for item in items),
            missing_count=sum(item.status == "missing" for item in items),
            oldest_nav_date=min(dated_items) if dated_items else None,
            items=sorted(
                items,
                key=lambda item: (
                    {"missing": 0, "stale": 1, "fresh": 2}[item.status],
                    -(item.business_day_age or 0),
                    item.fund_code,
                ),
            ),
        )

    def sync_held_fund_profiles(self) -> FundProfileSyncRead:
        funds_by_id = {
            position.fund_id: position.fund
            for position in self.repository.list_positions()
        }
        source = self.nav_source or self._build_default_nav_source()
        items: list[FundProfileSyncItemRead] = []

        for fund_id in sorted(funds_by_id):
            fund = funds_by_id[fund_id]
            previous_type = fund.fund_type
            try:
                detected_type = source.fetch_profile_type(fund.code)
                current_type = self._normalize_profile_fund_type(
                    detected_type,
                    previous_type,
                )
                status = (
                    "updated"
                    if current_type != previous_type
                    else "unchanged"
                )
                if status == "updated":
                    self.repository.upsert_fund(
                        code=fund.code,
                        name=fund.name,
                        fund_type=current_type,
                    )
                items.append(
                    FundProfileSyncItemRead(
                        fund_code=fund.code,
                        fund_name=fund.name,
                        previous_type=previous_type,
                        detected_type=detected_type,
                        current_type=current_type,
                        status=status,
                        message=(
                            "Fund type normalized from profile."
                            if status == "updated"
                            else "Existing fund type retained."
                        ),
                    )
                )
            except Exception as exc:
                message = (
                    exc.message
                    if isinstance(exc, AppError)
                    else "Fund profile sync failed."
                )
                logger.warning(
                    "Fund profile sync failed for {}: {}",
                    fund.code,
                    exc,
                )
                items.append(
                    FundProfileSyncItemRead(
                        fund_code=fund.code,
                        fund_name=fund.name,
                        previous_type=previous_type,
                        detected_type=None,
                        current_type=previous_type,
                        status="failed",
                        message=message,
                    )
                )

        if any(item.status == "updated" for item in items):
            self.repository.commit()
        return FundProfileSyncRead(
            total=len(items),
            updated=sum(item.status == "updated" for item in items),
            unchanged=sum(item.status == "unchanged" for item in items),
            failed=sum(item.status == "failed" for item in items),
            items=items,
        )

    @staticmethod
    def _normalize_profile_fund_type(
        detected_type: str,
        fallback_type: str,
    ) -> str:
        if "QDII" in detected_type.upper() or "\u6d77\u5916" in detected_type:
            return "QDII"
        return fallback_type

    def _resolve_fund_type(
        self,
        fund_code: str,
        fallback_type: str,
        *,
        source: EastmoneyFundNavSource | None = None,
    ) -> str:
        if "QDII" in fallback_type.upper():
            return "QDII"

        profile_source = source or self.nav_source or self._build_default_nav_source()
        if not hasattr(profile_source, "fetch_profile_type"):
            return fallback_type
        try:
            detected_type = profile_source.fetch_profile_type(fund_code)
        except Exception as exc:
            logger.warning(
                "Fund type detection failed for {}; retaining {}: {}",
                fund_code,
                fallback_type,
                exc,
            )
            return fallback_type
        return self._normalize_profile_fund_type(detected_type, fallback_type)

    def list_transactions(self, limit: int = 100) -> list[FundTransactionRead]:
        bounded_limit = max(1, min(limit, 500))
        return [
            self._to_transaction_read(transaction)
            for transaction in self.repository.list_transactions(limit=bounded_limit)
        ]

    def list_watchlist_items(self) -> list[FundWatchlistRead]:
        return [self._to_watchlist_read(item) for item in self.repository.list_watchlist_items()]

    def list_nav_records(self, limit: int = 50) -> list[FundNavRecordRead]:
        bounded_limit = max(1, min(limit, 200))
        return [
            self._to_nav_record_read(record)
            for record in self.repository.list_nav_records(limit=bounded_limit)
        ]

    def list_nav_history(self, fund_code: str, limit: int = 365) -> list[FundNavRecordRead]:
        bounded_limit = max(2, min(limit, 500))
        return [
            self._to_nav_record_read(record)
            for record in self.repository.list_nav_history(
                fund_code=fund_code.strip(),
                limit=bounded_limit,
            )
        ]

    def get_nav_risk(self, fund_code: str, limit: int = 365) -> FundNavRiskRead:
        records = self.repository.list_nav_history(
            fund_code=fund_code.strip(),
            limit=max(2, min(limit, 500)),
        )
        metrics = calculate_nav_risk(
            [(record.nav_date, record.unit_nav) for record in records]
        )
        fund_name = records[-1].fund.name if records else fund_code.strip()
        calculation_available = metrics.sample_count >= 2
        if metrics.sample_count >= 3:
            warning = (
                "波动率按日收益标准差乘以全年252个交易日年化；"
                "最大回撤按样本内历史峰值到后续谷值计算。"
            )
        elif calculation_available:
            warning = "当前只能计算区间收益和最大回撤；年化波动率至少需要三个交易日净值。"
        else:
            warning = "至少需要两个交易日的净值，才能计算区间收益和最大回撤。"
        return FundNavRiskRead(
            fund_code=fund_code.strip(),
            fund_name=fund_name,
            sample_count=metrics.sample_count,
            return_observation_count=metrics.return_observation_count,
            start_date=metrics.start_date,
            end_date=metrics.end_date,
            cumulative_return=metrics.cumulative_return,
            annualized_volatility=metrics.annualized_volatility,
            maximum_drawdown=metrics.maximum_drawdown,
            drawdown_peak_date=metrics.drawdown_peak_date,
            drawdown_trough_date=metrics.drawdown_trough_date,
            positive_day_ratio=metrics.positive_day_ratio,
            calculation_available=calculation_available,
            warning=warning,
        )

    def create_nav_record(self, payload: FundNavRecordCreate) -> FundNavRecordRead:
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=payload.fund_type,
        )
        record = self.repository.upsert_nav_record(
            fund=fund,
            nav_date=payload.nav_date,
            unit_nav=payload.unit_nav,
            accumulated_nav=payload.accumulated_nav,
            source=payload.source,
            note=payload.note,
        )
        self.repository.update_position_navs(fund_id=fund.id, current_nav=payload.unit_nav)
        self.repository.commit()
        return self._to_nav_record_read(record)

    def sync_latest_nav(self, payload: FundNavSyncLatestRequest) -> FundNavRecordRead:
        latest = self._fetch_latest_nav(payload.fund_code, payload.fund_type)
        return self._persist_latest_nav(latest)

    def import_ttskill_base_infos(
        self,
        payload: dict[str, object],
    ) -> FundNavRecordRead:
        latest = TtSkillBaseInfoSource().parse(payload)
        return self._persist_latest_nav(latest)

    def import_ttskill_nav_info(
        self,
        payload: dict[str, object],
    ) -> FundNavRecordRead:
        latest = TtSkillNavInfoSource().parse(payload)
        return self._persist_latest_nav(latest)

    def import_ttskill_account_holdings(
        self,
        payload: dict[str, object],
    ) -> FundAccountSnapshotRead:
        source = TtSkillAccountHoldingSource()
        holdings = source.parse(payload)
        snapshot = self.repository.create_account_snapshot(
            source=source.source,
            account_label=source.account_label,
            contract_version=source.contract_version,
            captured_at=utcnow(),
            holdings=[
                (
                    holding.asset_code,
                    holding.asset_name,
                    holding.asset_type,
                    holding.asset_value,
                    holding.daily_profit,
                    holding.hold_profit,
                    holding.hold_profit_rate,
                    holding.constant_profit,
                    holding.constant_profit_rate,
                )
                for holding in holdings
            ],
        )
        self.repository.commit()
        return self._to_account_snapshot_read(snapshot)

    def get_latest_ttskill_account_holdings(
        self,
    ) -> FundAccountSnapshotRead | None:
        snapshot = self.repository.get_latest_account_snapshot()
        return (
            self._to_account_snapshot_read(snapshot)
            if snapshot is not None
            else None
        )

    def sync_nav_history(self, payload: FundNavHistorySyncRequest) -> FundNavHistorySyncRead:
        history = self._fetch_nav_history(
            fund_code=payload.fund_code,
            fund_type=payload.fund_type,
            limit=payload.limit,
        )
        return self._persist_nav_history(history)

    def sync_holding_history(self, limit: int = 365) -> FundHoldingHistorySyncRead:
        bounded_limit = max(2, min(limit, 500))
        targets_by_code: dict[str, tuple[str, str]] = {}
        for position in self.repository.list_positions():
            targets_by_code[position.fund.code] = (
                position.fund.name,
                position.fund.fund_type,
            )
        targets = [
            (fund_code, fund_name, fund_type)
            for fund_code, (fund_name, fund_type) in sorted(targets_by_code.items())
        ]
        if not targets:
            return FundHoldingHistorySyncRead(
                total=0,
                succeeded=0,
                failed=0,
                synced_count=0,
                items=[],
            )

        configured_workers = self.settings.fund_nav_sync_max_workers if self.settings else 4
        with ThreadPoolExecutor(max_workers=min(configured_workers, len(targets))) as executor:
            futures = [
                executor.submit(
                    self._fetch_nav_history,
                    fund_code,
                    fund_type,
                    bounded_limit,
                )
                for fund_code, _, fund_type in targets
            ]

        results: list[FundHoldingHistorySyncItemRead] = []
        for (fund_code, fund_name, _), future in zip(targets, futures, strict=True):
            try:
                history = future.result()
                synced = self._persist_nav_history(history)
                results.append(
                    FundHoldingHistorySyncItemRead(
                        fund_code=synced.fund_code,
                        fund_name=synced.fund_name,
                        status="succeeded",
                        synced_count=synced.synced_count,
                        earliest_date=synced.earliest_date,
                        latest_date=synced.latest_date,
                        source=synced.source,
                    )
                )
            except Exception as exc:
                self.repository.rollback()
                message = exc.message if isinstance(exc, AppError) else "History NAV sync failed."
                logger.warning(
                    "Fund holding history sync failed for {}: {}",
                    fund_code,
                    exc,
                )
                results.append(
                    FundHoldingHistorySyncItemRead(
                        fund_code=fund_code,
                        fund_name=fund_name,
                        status="failed",
                        message=message,
                    )
                )

        succeeded = sum(item.status == "succeeded" for item in results)
        return FundHoldingHistorySyncRead(
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            synced_count=sum(item.synced_count for item in results),
            items=results,
        )

    def _fetch_nav_history(
        self,
        fund_code: str,
        fund_type: str,
        limit: int,
    ) -> list[FundLatestNav]:
        source = self.nav_source or self._build_default_nav_source()
        resolved_type = self._resolve_fund_type(
            fund_code,
            fund_type,
            source=source,
        )
        return source.fetch_history(
            fund_code=fund_code,
            fund_type=resolved_type,
            limit=limit,
        )

    def _persist_nav_history(
        self,
        history: list[FundLatestNav],
    ) -> FundNavHistorySyncRead:
        latest = history[-1]
        fund = self.repository.upsert_fund(
            code=latest.fund_code,
            name=latest.fund_name,
            fund_type=latest.fund_type,
            source=latest.source,
        )
        self.repository.upsert_nav_records(
            fund=fund,
            records=[
                (
                    item.nav_date,
                    item.unit_nav,
                    item.accumulated_nav,
                    item.source,
                    f"source_url={item.source_url}",
                )
                for item in history
            ],
        )
        self.repository.update_position_navs(
            fund_id=fund.id,
            current_nav=latest.unit_nav,
        )
        self.repository.commit()
        return FundNavHistorySyncRead(
            fund_code=latest.fund_code,
            fund_name=latest.fund_name,
            fund_type=latest.fund_type,
            synced_count=len(history),
            earliest_date=history[0].nav_date,
            latest_date=latest.nav_date,
            source=latest.source,
        )

    def sync_watchlist_navs(self) -> FundWatchlistNavSyncRead:
        items = self.repository.list_watchlist_items()
        targets = [
            (item.fund.code, item.fund.name, item.fund.fund_type)
            for item in items
        ]
        result = self._sync_latest_targets(targets)
        return FundWatchlistNavSyncRead(**result.model_dump())

    def sync_tracked_navs(self) -> FundTrackedNavSyncRead:
        targets_by_code: dict[str, tuple[str, str]] = {}
        for position in self.repository.list_positions():
            targets_by_code[position.fund.code] = (
                position.fund.name,
                position.fund.fund_type,
            )
        for item in self.repository.list_watchlist_items():
            targets_by_code[item.fund.code] = (
                item.fund.name,
                item.fund.fund_type,
            )
        targets = [
            (fund_code, fund_name, fund_type)
            for fund_code, (fund_name, fund_type) in sorted(targets_by_code.items())
        ]
        return self._sync_latest_targets(targets)

    def _sync_latest_targets(
        self,
        targets: list[tuple[str, str, str]],
    ) -> FundTrackedNavSyncRead:
        if not targets:
            return FundTrackedNavSyncRead(
                total=0,
                succeeded=0,
                failed=0,
                updated=0,
                items=[],
            )

        results: list[FundWatchlistNavSyncItemRead] = []
        configured_workers = self.settings.fund_nav_sync_max_workers if self.settings else 4
        with ThreadPoolExecutor(max_workers=min(configured_workers, len(targets))) as executor:
            futures = [
                executor.submit(self._fetch_latest_nav, fund_code, fund_type)
                for fund_code, _, fund_type in targets
            ]

        for (fund_code, fund_name, _), future in zip(targets, futures, strict=True):
            try:
                latest = future.result()
                existing = self.repository.list_nav_history(
                    fund_code=fund_code,
                    limit=2,
                )
                previous_date = existing[-1].nav_date if existing else None
                self._persist_latest_nav(latest)
                results.append(
                    FundWatchlistNavSyncItemRead(
                        fund_code=latest.fund_code,
                        fund_name=latest.fund_name,
                        status="succeeded",
                        nav_date=latest.nav_date,
                        unit_nav=latest.unit_nav,
                        updated=(
                            previous_date is None or latest.nav_date > previous_date
                        ),
                    )
                )
            except Exception as exc:
                self.repository.rollback()
                message = exc.message if isinstance(exc, AppError) else "Latest NAV sync failed."
                logger.warning(
                    "Fund watchlist NAV sync failed for {}: {}",
                    fund_code,
                    exc,
                )
                results.append(
                    FundWatchlistNavSyncItemRead(
                        fund_code=fund_code,
                        fund_name=fund_name,
                        status="failed",
                        message=message,
                    )
                )

        succeeded = len([item for item in results if item.status == "succeeded"])
        return FundTrackedNavSyncRead(
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            updated=len([item for item in results if item.updated]),
            items=results,
        )

    def _fetch_latest_nav(self, fund_code: str, fund_type: str) -> FundLatestNav:
        source = self.nav_source or self._build_default_nav_source()
        resolved_type = self._resolve_fund_type(
            fund_code,
            fund_type,
            source=source,
        )
        return source.fetch_latest(fund_code=fund_code, fund_type=resolved_type)

    def _persist_latest_nav(self, latest: FundLatestNav) -> FundNavRecordRead:
        fund = self.repository.upsert_fund(
            code=latest.fund_code,
            name=latest.fund_name,
            fund_type=latest.fund_type,
            source=latest.source,
        )
        record = self.repository.upsert_nav_record(
            fund=fund,
            nav_date=latest.nav_date,
            unit_nav=latest.unit_nav,
            accumulated_nav=latest.accumulated_nav,
            source=latest.source,
            note=f"source_url={latest.source_url}",
        )
        self.repository.update_position_navs(fund_id=fund.id, current_nav=latest.unit_nav)
        self.repository.commit()
        return self._to_nav_record_read(record)

    def lookup_latest_nav(self, payload: FundNavSyncLatestRequest) -> FundLatestNavRead:
        latest = self._fetch_latest_nav(payload.fund_code, payload.fund_type)
        return FundLatestNavRead(
            fund_code=latest.fund_code,
            fund_name=latest.fund_name,
            fund_type=latest.fund_type,
            nav_date=latest.nav_date,
            unit_nav=latest.unit_nav,
            accumulated_nav=latest.accumulated_nav,
            source=latest.source,
            source_url=latest.source_url,
        )

    def delete_nav_record(self, record_id: int) -> None:
        record = self.repository.get_nav_record(record_id)
        if record is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Fund NAV record was not found.",
                status_code=404,
            )
        self.repository.delete_nav_record(record)
        self.repository.commit()

    def create_watchlist_item(self, payload: FundWatchlistCreate) -> FundWatchlistRead:
        fund_type = self._resolve_fund_type(payload.fund_code, payload.fund_type)
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=fund_type,
        )
        existing = self.repository.get_watchlist_item_by_fund_id(fund.id)
        if existing is not None:
            item = self.repository.update_watchlist_item(
                existing,
                fund=fund,
                priority=payload.priority,
                status=payload.status,
                watch_reason=payload.watch_reason,
                risk_level=payload.risk_level,
                target_position=payload.target_position,
                tags=payload.tags,
                note=payload.note,
            )
        else:
            item = self.repository.create_watchlist_item(
                fund=fund,
                priority=payload.priority,
                status=payload.status,
                watch_reason=payload.watch_reason,
                risk_level=payload.risk_level,
                target_position=payload.target_position,
                tags=payload.tags,
                note=payload.note,
            )
        self.repository.commit()
        return self._to_watchlist_read(item)

    def update_watchlist_item(
        self,
        item_id: int,
        payload: FundWatchlistUpdate,
    ) -> FundWatchlistRead:
        item = self.repository.get_watchlist_item(item_id)
        if item is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Fund watchlist item was not found.",
                status_code=404,
            )
        fund_type = self._resolve_fund_type(payload.fund_code, payload.fund_type)
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=fund_type,
        )
        existing = self.repository.get_watchlist_item_by_fund_id(fund.id)
        if existing is not None and existing.id != item_id:
            raise AppError(
                code=ErrorCode.conflict,
                message="Fund is already in the watchlist.",
                status_code=409,
            )
        updated = self.repository.update_watchlist_item(
            item,
            fund=fund,
            priority=payload.priority,
            status=payload.status,
            watch_reason=payload.watch_reason,
            risk_level=payload.risk_level,
            target_position=payload.target_position,
            tags=payload.tags,
            note=payload.note,
        )
        self.repository.commit()
        return self._to_watchlist_read(updated)

    def delete_watchlist_item(self, item_id: int) -> None:
        item = self.repository.get_watchlist_item(item_id)
        if item is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Fund watchlist item was not found.",
                status_code=404,
            )
        self.repository.delete_watchlist_item(item)
        self.repository.commit()

    def create_position(self, payload: FundPositionCreate) -> FundPositionRead:
        fund_type = self._resolve_fund_type(payload.fund_code, payload.fund_type)
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=fund_type,
        )
        position = self.repository.create_position(
            fund=fund,
            account_name=payload.account_name,
            shares=payload.shares,
            cost_price=payload.cost_price,
            total_cost=payload.normalized_total_cost,
            current_nav=payload.current_nav,
            target_weight=payload.target_weight,
            opened_at=payload.opened_at,
            tags=payload.tags,
            note=payload.note,
        )
        self.repository.commit()
        return self._to_position_read(position)

    def update_position(self, position_id: int, payload: FundPositionUpdate) -> FundPositionRead:
        position = self.repository.get_position(position_id)
        if position is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Fund position was not found.",
                status_code=404,
            )

        fund_type = self._resolve_fund_type(payload.fund_code, payload.fund_type)
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=fund_type,
        )
        updated = self.repository.update_position(
            position,
            fund=fund,
            account_name=payload.account_name,
            shares=payload.shares,
            cost_price=payload.cost_price,
            total_cost=payload.normalized_total_cost,
            current_nav=payload.current_nav,
            target_weight=payload.target_weight,
            opened_at=payload.opened_at,
            tags=payload.tags,
            note=payload.note,
        )
        self.repository.commit()
        return self._to_position_read(updated)

    def delete_position(self, position_id: int) -> None:
        position = self.repository.get_position(position_id)
        if position is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Fund position was not found.",
                status_code=404,
            )
        self.repository.delete_position(position)
        self.repository.commit()

    def create_transaction(self, payload: FundTransactionCreate) -> FundTransactionRead:
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=payload.fund_type,
        )
        transaction = self.repository.create_transaction(
            fund=fund,
            account_name=payload.account_name,
            transaction_type=payload.transaction_type,
            trade_date=payload.trade_date,
            shares=payload.shares,
            unit_price=payload.unit_price,
            amount=payload.normalized_amount,
            fee=payload.fee,
            note=payload.note,
        )
        self.repository.commit()
        return self._to_transaction_read(transaction)

    def import_ttskill_trades(
        self,
        payload: FundTtSkillTradesImport,
        *,
        dry_run: bool,
    ) -> FundTtSkillTradesImportRead:
        source = TtSkillTradeQuerySource()
        bundle = source.parse_bundle(payload.list_payload, payload.detail_payloads)
        items: list[FundTtSkillTradeImportItemRead] = []
        for trade in bundle.trades:
            existing = self.repository.get_transaction_by_external_id(
                external_source=source.source,
                external_trade_id=trade.trade_id,
            )
            action, reason = self._trade_import_action(trade, existing is not None)
            transaction_id = existing.id if existing is not None else None
            if not dry_run and action == "create":
                transaction = self._create_imported_trade(payload.account_name, trade)
                transaction_id = transaction.id
            elif not dry_run and action == "update" and existing is not None:
                self._update_imported_trade(existing, payload.account_name, trade)
            items.append(
                FundTtSkillTradeImportItemRead(
                    trade_id=trade.trade_id,
                    fund_code=trade.fund_code,
                    fund_name=trade.fund_name,
                    business_type=trade.business_type,
                    trade_time=trade.trade_time,
                    action=action,
                    reason=reason,
                    transaction_id=transaction_id,
                )
            )
        if not dry_run:
            self.repository.commit()
        return FundTtSkillTradesImportRead(
            dry_run=dry_run,
            total=len(items),
            create_count=sum(item.action == "create" for item in items),
            update_count=sum(item.action == "update" for item in items),
            skip_count=sum(item.action == "skip" for item in items),
            error_count=sum(item.action == "error" for item in items),
            items=items,
        )

    @staticmethod
    def _trade_import_action(
        trade: TtSkillTrade,
        exists: bool,
    ) -> tuple[Literal["create", "update", "skip", "error"], str]:
        if trade.transaction_type is None:
            return "skip", "撤单或暂不支持的业务类型，不进入现金流流水。"
        if not trade.confirmed or trade.confirm_status != "confirmed":
            return "skip", "交易尚未确认成功，等待下次同步。"
        if trade.effective_amount is None or trade.effective_amount <= 0:
            return "error", "缺少有效确认金额。"
        if trade.transaction_type in {"buy", "sell"} and (
            trade.confirm_vol is None or trade.confirm_vol <= 0 or trade.nav is None or trade.nav <= 0
        ):
            return "error", "买入或卖出缺少确认份额或确认净值。"
        return ("update", "已存在，按最新详情更新。") if exists else ("create", "新流水。")

    def _create_imported_trade(self, account_name: str, trade: TtSkillTrade) -> FundTransactionModel:
        fund = self.repository.upsert_fund(
            code=trade.fund_code,
            name=trade.fund_name,
            fund_type="unknown",
            source="ttfund_skills",
        )
        return self.repository.create_transaction(
            fund=fund,
            account_name=account_name,
            transaction_type=trade.transaction_type or "fee",
            trade_date=trade.confirm_date or trade.trade_time.date(),
            shares=trade.confirm_vol,
            unit_price=trade.nav,
            amount=trade.effective_amount or Decimal("0"),
            fee=trade.charge,
            note=f"来源: 天天基金; 业务: {trade.business_type}",
            external_source="ttfund_skills",
            external_trade_id=trade.trade_id,
            external_trade_type=trade.trade_type,
            external_business_code=trade.business_code,
            external_status=trade.status_text,
            external_confirm_status=trade.confirm_status,
            confirm_date=trade.confirm_date,
            source_updated_at=trade.trade_time,
        )

    def _update_imported_trade(
        self,
        transaction: FundTransactionModel,
        account_name: str,
        trade: TtSkillTrade,
    ) -> None:
        fund = self.repository.upsert_fund(
            code=trade.fund_code,
            name=trade.fund_name,
            fund_type="unknown",
            source="ttfund_skills",
        )
        transaction.fund = fund
        transaction.account_name = account_name
        transaction.transaction_type = trade.transaction_type or transaction.transaction_type
        transaction.trade_date = trade.confirm_date or trade.trade_time.date()
        transaction.shares = trade.confirm_vol
        transaction.unit_price = trade.nav
        transaction.amount = trade.effective_amount or Decimal("0")
        transaction.fee = trade.charge
        transaction.note = f"来源: 天天基金; 业务: {trade.business_type}"
        transaction.external_trade_type = trade.trade_type
        transaction.external_business_code = trade.business_code
        transaction.external_status = trade.status_text
        transaction.external_confirm_status = trade.confirm_status
        transaction.confirm_date = trade.confirm_date
        transaction.source_updated_at = trade.trade_time
        transaction.updated_at = utcnow()

    def delete_transaction(self, transaction_id: int) -> None:
        transaction = self.repository.get_transaction(transaction_id)
        if transaction is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Fund transaction was not found.",
                status_code=404,
            )
        self.repository.delete_transaction(transaction)
        self.repository.commit()

    def get_transaction_summary(self) -> FundTransactionSummaryRead:
        transactions = self.repository.list_transactions(limit=None)
        total_buy = sum(
            (item.amount for item in transactions if item.transaction_type == "buy"),
            Decimal("0"),
        )
        total_sell = sum(
            (item.amount for item in transactions if item.transaction_type == "sell"),
            Decimal("0"),
        )
        total_dividend = sum(
            (item.amount for item in transactions if item.transaction_type == "dividend"),
            Decimal("0"),
        )
        explicit_fees = sum(
            (item.amount for item in transactions if item.transaction_type == "fee"),
            Decimal("0"),
        )
        attached_fees = sum((item.fee for item in transactions), Decimal("0"))
        net_cash_flow = sum(
            (self._transaction_cash_flow(item) for item in transactions),
            Decimal("0"),
        )
        return FundTransactionSummaryRead(
            transaction_count=len(transactions),
            total_buy=total_buy,
            total_sell=total_sell,
            total_dividend=total_dividend,
            total_fee=explicit_fees + attached_fees,
            net_cash_flow=net_cash_flow,
        )

    def get_cash_flow_performance(self) -> FundCashFlowPerformanceRead:
        transactions = self.repository.list_transactions(limit=None)
        positions = self.repository.list_positions()
        cash_flows = [self._transaction_cash_flow(item) for item in transactions]
        invested_cash = sum(
            (-cash_flow for cash_flow in cash_flows if cash_flow < 0),
            Decimal("0"),
        )
        recovered_cash = sum(
            (cash_flow for cash_flow in cash_flows if cash_flow > 0),
            Decimal("0"),
        )
        valued_positions = [
            position for position in positions if position.current_nav is not None
        ]
        valuation_complete = len(valued_positions) == len(positions)
        current_value = (
            sum(
                (
                    position.shares * position.current_nav
                    for position in valued_positions
                    if position.current_nav is not None
                ),
                Decimal("0"),
            )
            if valuation_complete
            else None
        )
        calculation_available = (
            bool(transactions)
            and invested_cash > 0
            and valuation_complete
        )
        net_profit = (
            current_value + recovered_cash - invested_cash
            if calculation_available and current_value is not None
            else None
        )
        simple_return_rate = (
            net_profit / invested_cash
            if net_profit is not None and invested_cash > 0
            else None
        )
        trade_dates = [transaction.trade_date for transaction in transactions]
        warning = self._cash_flow_performance_warning(
            transaction_count=len(transactions),
            invested_cash=invested_cash,
            valuation_complete=valuation_complete,
        )
        return FundCashFlowPerformanceRead(
            transaction_count=len(transactions),
            position_count=len(positions),
            valuation_complete=valuation_complete,
            calculation_available=calculation_available,
            invested_cash=invested_cash,
            recovered_cash=recovered_cash,
            current_value=current_value,
            net_profit=net_profit,
            simple_return_rate=simple_return_rate,
            earliest_trade_date=min(trade_dates) if trade_dates else None,
            latest_trade_date=max(trade_dates) if trade_dates else None,
            calculation_basis="已录入现金流 + 当前持仓市值",
            warning=warning,
        )

    def get_holding_summary(self) -> FundHoldingSummaryRead:
        positions = self.repository.list_positions()
        total_cost = sum((position.total_cost for position in positions), Decimal("0"))
        valued_positions = [
            position for position in positions if position.current_nav is not None
        ]
        current_value = sum(
            (position.shares * position.current_nav for position in valued_positions),
            Decimal("0"),
        )
        valued_cost = sum(
            (position.total_cost for position in valued_positions),
            Decimal("0"),
        )
        unrealized_profit = current_value - valued_cost if valued_positions else None
        unrealized_return_rate = (
            unrealized_profit / valued_cost
            if unrealized_profit is not None and valued_cost > 0
            else None
        )
        fund_types = sorted({position.fund.fund_type for position in positions})
        accounts = sorted({position.account_name for position in positions})
        return FundHoldingSummaryRead(
            position_count=len(positions),
            fund_count=len({position.fund_id for position in positions}),
            total_cost=total_cost,
            current_value=current_value if valued_positions else None,
            unrealized_profit=unrealized_profit,
            unrealized_return_rate=unrealized_return_rate,
            valued_position_count=len(valued_positions),
            fund_types=fund_types,
            accounts=accounts,
        )

    def get_allocation(self) -> FundAllocationRead:
        positions = self.repository.list_positions()
        valued = [
            (
                position,
                position.shares * position.current_nav
                if position.current_nav is not None
                else position.total_cost,
                "current_nav" if position.current_nav is not None else "cost",
            )
            for position in positions
        ]
        total_amount = sum((amount for _, amount, _ in valued), Decimal("0"))
        configured_target_count = len(
            [position for position in positions if position.target_weight is not None]
        )
        target_weight_total = sum(
            (
                position.target_weight
                for position in positions
                if position.target_weight is not None
            ),
            Decimal("0"),
        )
        target_configuration_complete = bool(positions) and (
            configured_target_count == len(positions)
            and abs(target_weight_total - Decimal("1")) <= Decimal("0.0001")
        )
        target_warning = self._target_allocation_warning(
            position_count=len(positions),
            configured_target_count=configured_target_count,
            target_weight_total=target_weight_total,
        )

        holdings = [
            FundAllocationHoldingRead(
                position_id=position.id,
                fund_code=position.fund.code,
                fund_name=position.fund.name,
                fund_type=position.fund.fund_type,
                account_name=position.account_name,
                amount=amount,
                weight=amount / total_amount if total_amount > 0 else Decimal("0"),
                target_weight=position.target_weight,
                weight_deviation=(
                    amount / total_amount - position.target_weight
                    if total_amount > 0 and position.target_weight is not None
                    else None
                ),
                target_amount=(
                    total_amount * position.target_weight
                    if position.target_weight is not None
                    else None
                ),
                calibration_amount=(
                    total_amount * position.target_weight - amount
                    if position.target_weight is not None
                    else None
                ),
                valuation_basis=basis,
            )
            for position, amount, basis in valued
        ]
        holdings.sort(key=lambda item: (-item.amount, item.fund_code, item.account_name))
        fund_amounts: dict[str, Decimal] = {}
        for holding in holdings:
            fund_amounts[holding.fund_code] = (
                fund_amounts.get(holding.fund_code, Decimal("0"))
                + holding.amount
            )
        fund_weights = [
            amount / total_amount if total_amount > 0 else Decimal("0")
            for amount in fund_amounts.values()
        ]
        return FundAllocationRead(
            position_count=len(positions),
            total_amount=total_amount,
            current_nav_count=len(
                [position for position in positions if position.current_nav is not None]
            ),
            cost_fallback_count=len(
                [position for position in positions if position.current_nav is None]
            ),
            top_holding_weight=max(fund_weights, default=None),
            concentration_hhi=(
                sum((weight * weight for weight in fund_weights), Decimal("0"))
                if fund_weights
                else None
            ),
            configured_target_count=configured_target_count,
            target_weight_total=target_weight_total,
            target_configuration_complete=target_configuration_complete,
            target_warning=target_warning,
            by_fund_type=self._build_allocation_groups(
                valued,
                total_amount=total_amount,
                group_by="fund_type",
            ),
            by_account=self._build_allocation_groups(
                valued,
                total_amount=total_amount,
                group_by="account",
            ),
            holdings=holdings,
        )

    @staticmethod
    def _target_allocation_warning(
        *,
        position_count: int,
        configured_target_count: int,
        target_weight_total: Decimal,
    ) -> str:
        if position_count == 0:
            return ""
        if configured_target_count == 0:
            return "尚未设置目标占比，当前仅展示实际配置。"
        if configured_target_count < position_count:
            return (
                f"已设置 {configured_target_count}/{position_count} 条持仓的目标占比，"
                "补齐后才能完整比较配置偏离。"
            )
        if abs(target_weight_total - Decimal("1")) > Decimal("0.0001"):
            return (
                f"目标占比合计为 {target_weight_total * 100:.2f}%，"
                "应调整为 100% 后再解读校准金额。"
            )
        return "目标占比配置完整；校准金额仅用于结构测算，不构成交易建议。"

    def get_holding_risk(self, limit: int = 365) -> FundHoldingRiskRead:
        bounded_limit = max(2, min(limit, 500))
        allocation = self.get_allocation()
        grouped: dict[str, dict[str, str | int | Decimal]] = {}
        for holding in allocation.holdings:
            entry = grouped.setdefault(
                holding.fund_code,
                {
                    "fund_name": holding.fund_name,
                    "fund_type": holding.fund_type,
                    "position_count": 0,
                    "allocation_weight": Decimal("0"),
                },
            )
            entry["position_count"] = int(entry["position_count"]) + 1
            entry["allocation_weight"] = (
                Decimal(entry["allocation_weight"]) + holding.weight
            )

        items: list[FundHoldingRiskItemRead] = []
        for fund_code, entry in grouped.items():
            risk = self.get_nav_risk(fund_code=fund_code, limit=bounded_limit)
            items.append(
                FundHoldingRiskItemRead(
                    fund_code=fund_code,
                    fund_name=str(entry["fund_name"]),
                    fund_type=str(entry["fund_type"]),
                    position_count=int(entry["position_count"]),
                    allocation_weight=Decimal(entry["allocation_weight"]),
                    sample_count=risk.sample_count,
                    start_date=risk.start_date,
                    end_date=risk.end_date,
                    cumulative_return=risk.cumulative_return,
                    annualized_volatility=risk.annualized_volatility,
                    maximum_drawdown=risk.maximum_drawdown,
                    positive_day_ratio=risk.positive_day_ratio,
                    calculation_available=risk.calculation_available,
                )
            )
        items.sort(key=lambda item: (-item.allocation_weight, item.fund_code))
        return FundHoldingRiskRead(
            fund_count=len(items),
            analyzed_fund_count=sum(item.calculation_available for item in items),
            sample_limit=bounded_limit,
            items=items,
            warning=(
                "每只基金按自身最近净值样本独立计算，仓位占比仅用于排序和识别风险暴露；"
                "本表不是组合波动率，也未计算基金之间的相关性。"
            ),
        )

    def get_portfolio_performance(
        self,
        limit: int = 365,
    ) -> FundPortfolioPerformanceRead:
        bounded_limit = max(2, min(limit, 500))
        allocation = self.get_allocation()
        grouped: dict[str, dict[str, str | Decimal]] = {}
        for holding in allocation.holdings:
            entry = grouped.setdefault(
                holding.fund_code,
                {
                    "fund_name": holding.fund_name,
                    "allocation_weight": Decimal("0"),
                },
            )
            entry["allocation_weight"] = (
                Decimal(entry["allocation_weight"]) + holding.weight
            )

        members: list[FundPortfolioMemberRead] = []
        portfolio_series: list[PortfolioFundSeries] = []
        excluded_fund_codes: list[str] = []
        for fund_code, entry in grouped.items():
            records = self.repository.list_nav_history(
                fund_code=fund_code,
                limit=bounded_limit,
            )
            if len(records) < 2:
                excluded_fund_codes.append(fund_code)
                continue
            weight = Decimal(entry["allocation_weight"])
            members.append(
                FundPortfolioMemberRead(
                    fund_code=fund_code,
                    fund_name=str(entry["fund_name"]),
                    allocation_weight=weight,
                    sample_count=len(records),
                )
            )
            portfolio_series.append(
                PortfolioFundSeries(
                    fund_code=fund_code,
                    weight=weight,
                    observations=[
                        (record.nav_date, record.unit_nav)
                        for record in records
                    ],
                )
            )

        metrics = calculate_static_portfolio_performance(portfolio_series)
        calculation_available = len(metrics.points) >= 2
        members.sort(key=lambda item: (-item.allocation_weight, item.fund_code))
        return FundPortfolioPerformanceRead(
            fund_count=len(grouped),
            included_fund_count=len(members),
            sample_limit=bounded_limit,
            sample_count=len(metrics.points),
            start_date=metrics.risk.start_date,
            end_date=metrics.risk.end_date,
            valuation_complete=allocation.cost_fallback_count == 0,
            cumulative_return=metrics.risk.cumulative_return,
            equal_weight_return=metrics.equal_weight_return,
            annualized_volatility=metrics.risk.annualized_volatility,
            maximum_drawdown=metrics.risk.maximum_drawdown,
            calculation_available=calculation_available,
            members=members,
            excluded_fund_codes=sorted(excluded_fund_codes),
            points=[
                FundPortfolioPerformancePointRead(
                    nav_date=point.nav_date,
                    portfolio_index=point.portfolio_index,
                    equal_weight_index=point.equal_weight_index,
                    drawdown=point.drawdown,
                )
                for point in metrics.points
            ],
            warning=(
                "这是用当前持仓权重对共同净值日期进行的静态回放，不代表账户真实历史收益；"
                "未计入历史调仓、申购赎回、费用和分红。等权线只用于观察当前仓位权重的影响。"
            ),
        )

    def get_portfolio_benchmark(
        self,
        benchmark_code: str,
        limit: int = 365,
    ) -> FundPortfolioBenchmarkRead:
        bounded_limit = max(3, min(limit, 500))
        code = benchmark_code.strip()
        portfolio = self.get_portfolio_performance(limit=bounded_limit)
        benchmark_records = self.repository.list_nav_history(
            fund_code=code,
            limit=bounded_limit,
        )
        metrics = calculate_portfolio_benchmark(
            [
                (point.nav_date, point.portfolio_index)
                for point in portfolio.points
            ],
            [
                (record.nav_date, record.unit_nav)
                for record in benchmark_records
            ],
        )
        benchmark_name = (
            benchmark_records[-1].fund.name
            if benchmark_records
            else code
        )
        return FundPortfolioBenchmarkRead(
            benchmark_code=code,
            benchmark_name=benchmark_name,
            sample_limit=bounded_limit,
            sample_count=len(metrics.points),
            start_date=metrics.points[0].nav_date if metrics.points else None,
            end_date=metrics.points[-1].nav_date if metrics.points else None,
            portfolio_return=metrics.portfolio_return,
            benchmark_return=metrics.benchmark_return,
            relative_return=metrics.relative_return,
            tracking_error=metrics.tracking_error,
            information_ratio=metrics.information_ratio,
            return_correlation=metrics.return_correlation,
            calculation_available=len(metrics.points) >= 2,
            points=[
                FundPortfolioBenchmarkPointRead(
                    nav_date=point.nav_date,
                    portfolio_index=point.portfolio_index,
                    benchmark_index=point.benchmark_index,
                    relative_return=point.relative_return,
                )
                for point in metrics.points
            ],
            warning=(
                "基准使用基金净值作为指数代理，只在组合与基准都有净值的共同日期进行比较。"
                "结果受代理基金费用、跟踪误差、QDII 时区和净值发布日期影响，"
                "不等同于指数本身，也不构成投资建议。"
            ),
        )

    def get_holding_correlation(
        self,
        limit: int = 365,
    ) -> FundHoldingCorrelationRead:
        bounded_limit = max(3, min(limit, 500))
        allocation = self.get_allocation()
        grouped: dict[str, dict[str, str | Decimal]] = {}
        for holding in allocation.holdings:
            entry = grouped.setdefault(
                holding.fund_code,
                {
                    "fund_name": holding.fund_name,
                    "allocation_weight": Decimal("0"),
                },
            )
            entry["allocation_weight"] = (
                Decimal(entry["allocation_weight"]) + holding.weight
            )

        members: list[FundCorrelationMemberRead] = []
        series: list[FundCorrelationSeries] = []
        for fund_code, entry in grouped.items():
            records = self.repository.list_nav_history(
                fund_code=fund_code,
                limit=bounded_limit,
            )
            members.append(
                FundCorrelationMemberRead(
                    fund_code=fund_code,
                    fund_name=str(entry["fund_name"]),
                    allocation_weight=Decimal(entry["allocation_weight"]),
                    sample_count=len(records),
                )
            )
            series.append(
                FundCorrelationSeries(
                    fund_code=fund_code,
                    observations=[
                        (record.nav_date, record.unit_nav)
                        for record in records
                    ],
                )
            )

        calculated = calculate_holding_correlations(series)
        valid_values = [
            item.correlation
            for item in calculated
            if item.correlation is not None
        ]
        members.sort(key=lambda item: (-item.allocation_weight, item.fund_code))
        return FundHoldingCorrelationRead(
            fund_count=len(members),
            sample_limit=bounded_limit,
            calculated_pair_count=len(valid_values),
            total_pair_count=len(calculated),
            average_pairwise_correlation=(
                (
                    sum(valid_values, Decimal("0"))
                    / Decimal(len(valid_values))
                ).quantize(Decimal("0.000001"))
                if valid_values
                else None
            ),
            high_correlation_pair_count=sum(
                value >= Decimal("0.8") for value in valid_values
            ),
            members=members,
            pairs=[
                FundCorrelationPairRead(
                    first_fund_code=item.first_fund_code,
                    second_fund_code=item.second_fund_code,
                    observation_count=item.observation_count,
                    correlation=item.correlation,
                )
                for item in calculated
            ],
            warning=(
                "相关性基于两只基金相邻共同净值日期的收益率计算，只描述所选样本内的同步程度；"
                "相关性会随市场阶段变化，不代表未来关系，也不能替代底层资产穿透分析。"
            ),
        )

    def get_risk_contribution(
        self,
        limit: int = 365,
    ) -> FundRiskContributionRead:
        bounded_limit = max(3, min(limit, 500))
        allocation = self.get_allocation()
        grouped: dict[str, dict[str, str | Decimal]] = {}
        for holding in allocation.holdings:
            entry = grouped.setdefault(
                holding.fund_code,
                {
                    "fund_name": holding.fund_name,
                    "allocation_weight": Decimal("0"),
                },
            )
            entry["allocation_weight"] = (
                Decimal(entry["allocation_weight"]) + holding.weight
            )

        series: list[FundRiskContributionSeries] = []
        included_names: dict[str, str] = {}
        excluded_fund_codes: list[str] = []
        for fund_code, entry in grouped.items():
            records = self.repository.list_nav_history(
                fund_code=fund_code,
                limit=bounded_limit,
            )
            if len(records) < 3:
                excluded_fund_codes.append(fund_code)
                continue
            included_names[fund_code] = str(entry["fund_name"])
            series.append(
                FundRiskContributionSeries(
                    fund_code=fund_code,
                    weight=Decimal(entry["allocation_weight"]),
                    observations=[
                        (record.nav_date, record.unit_nav)
                        for record in records
                    ],
                )
            )

        metrics = calculate_risk_contributions(series)
        items = [
            FundRiskContributionItemRead(
                fund_code=item.fund_code,
                fund_name=included_names[item.fund_code],
                allocation_weight=item.allocation_weight,
                annualized_volatility=item.annualized_volatility,
                component_volatility=item.component_volatility,
                contribution_ratio=item.contribution_ratio,
            )
            for item in metrics.items
        ]
        items.sort(
            key=lambda item: (-item.contribution_ratio, item.fund_code)
        )
        return FundRiskContributionRead(
            fund_count=len(grouped),
            included_fund_count=len(series),
            sample_limit=bounded_limit,
            sample_count=metrics.sample_count,
            start_date=metrics.start_date,
            end_date=metrics.end_date,
            portfolio_annualized_volatility=(
                metrics.portfolio_annualized_volatility
            ),
            weighted_standalone_volatility=(
                metrics.weighted_standalone_volatility
            ),
            diversification_ratio=metrics.diversification_ratio,
            calculation_available=(
                metrics.portfolio_annualized_volatility is not None
                and bool(items)
            ),
            items=items,
            excluded_fund_codes=sorted(excluded_fund_codes),
            warning=(
                "风险贡献使用当前持仓权重与共同净值日期的历史收益协方差计算；"
                "它说明样本内各基金对组合波动的贡献，不代表未来风险，"
                "也不等同于基金金额占比或投资建议。"
            ),
        )

    def sync_holding_disclosures(self) -> FundDisclosureSyncRead:
        target_links = self._effective_target_links()
        targets_by_code: dict[str, tuple[str, str]] = {}
        for position in self.repository.list_positions():
            targets_by_code[position.fund.code] = (
                position.fund.name,
                position.fund.fund_type,
            )
        for link in target_links:
            if link.parent_fund_code in targets_by_code:
                targets_by_code.setdefault(
                    link.target_fund_code,
                    (link.target_fund_name, "ETF"),
                )
        targets = [
            (fund_code, fund_name, fund_type)
            for fund_code, (fund_name, fund_type) in sorted(
                targets_by_code.items()
            )
        ]
        if not targets:
            return FundDisclosureSyncRead(
                total=0,
                succeeded=0,
                failed=0,
                items=[],
            )

        configured_workers = (
            self.settings.fund_nav_sync_max_workers if self.settings else 4
        )
        with ThreadPoolExecutor(
            max_workers=min(configured_workers, len(targets))
        ) as executor:
            futures = [
                executor.submit(
                    self._fetch_holding_disclosure,
                    fund_code,
                )
                for fund_code, _, _ in targets
            ]

        items: list[FundDisclosureSyncItemRead] = []
        for (fund_code, fund_name, fund_type), future in zip(
            targets,
            futures,
            strict=True,
        ):
            try:
                disclosure = future.result()
                fund = self.repository.upsert_fund(
                    code=fund_code,
                    name=disclosure.fund_name or fund_name,
                    fund_type=fund_type,
                )
                self.repository.upsert_disclosure(
                    fund=fund,
                    report_date=disclosure.report_date,
                    report_period=disclosure.report_period,
                    asset_type=disclosure.asset_type,
                    source=disclosure.source,
                    source_url=disclosure.source_url,
                    holdings=[
                        (
                            holding.rank,
                            holding.asset_type,
                            holding.asset_code,
                            holding.asset_name,
                            holding.nav_ratio,
                            holding.reported_quantity,
                            holding.reported_market_value,
                        )
                        for holding in disclosure.holdings
                    ],
                )
                self.repository.commit()
                items.append(
                    FundDisclosureSyncItemRead(
                        fund_code=fund_code,
                        fund_name=disclosure.fund_name,
                        status="synced",
                        report_date=disclosure.report_date,
                        holding_count=len(disclosure.holdings),
                        message="",
                    )
                )
            except Exception as exc:
                self.repository.rollback()
                message = (
                    exc.message
                    if isinstance(exc, AppError)
                    else "Fund disclosure sync failed."
                )
                logger.warning(
                    "Fund disclosure sync failed for {}: {}",
                    fund_code,
                    exc,
                )
                items.append(
                    FundDisclosureSyncItemRead(
                        fund_code=fund_code,
                        fund_name=fund_name,
                        status="failed",
                        report_date=None,
                        holding_count=0,
                        message=message,
                    )
                )

        succeeded = sum(item.status == "synced" for item in items)
        return FundDisclosureSyncRead(
            total=len(items),
            succeeded=succeeded,
            failed=len(items) - succeeded,
            items=items,
        )

    def get_lookthrough(
        self,
        *,
        stale_after_days: int = 180,
    ) -> FundLookthroughRead:
        bounded_stale_days = max(30, min(stale_after_days, 730))
        as_of_date = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        allocation = self.get_allocation()
        grouped: dict[str, dict[str, str | int | Decimal]] = {}
        for holding in allocation.holdings:
            fund = self.repository.get_fund_by_code(holding.fund_code)
            if fund is None:
                continue
            entry = grouped.setdefault(
                holding.fund_code,
                {
                    "fund_id": fund.id,
                    "fund_name": holding.fund_name,
                    "allocation_weight": Decimal("0"),
                },
            )
            entry["allocation_weight"] = (
                Decimal(entry["allocation_weight"]) + holding.weight
            )

        target_links = self._effective_target_links()
        links_by_parent = {
            link.parent_fund_code: link for link in target_links
        }
        lookup_codes = set(grouped) | {
            link.target_fund_code
            for link in target_links
            if link.parent_fund_code in grouped
        }
        funds_by_code = {
            fund_code: fund
            for fund_code in lookup_codes
            if (fund := self.repository.get_fund_by_code(fund_code)) is not None
        }
        records = self.repository.list_latest_disclosures(
            fund_ids=[fund.id for fund in funds_by_code.values()],
        )
        records_by_code = {record.fund.code: record for record in records}
        domain_disclosures: list[LookthroughFundDisclosure] = []
        snapshots: list[FundLookthroughSnapshotRead] = []
        for fund_code, entry in grouped.items():
            record = records_by_code.get(fund_code)
            allocation_weight = Decimal(entry["allocation_weight"])
            direct_current = self._is_current_disclosure(
                record,
                as_of_date=as_of_date,
                stale_after_days=bounded_stale_days,
            )
            link = links_by_parent.get(fund_code)
            target_record = (
                records_by_code.get(link.target_fund_code)
                if link is not None
                else None
            )
            link_age_days = (
                (as_of_date - link.report_date).days
                if link is not None
                else None
            )
            target_current = (
                link is not None
                and link_age_days is not None
                and 0 <= link_age_days <= bounded_stale_days
                and self._is_current_disclosure(
                    target_record,
                    as_of_date=as_of_date,
                    stale_after_days=bounded_stale_days,
                )
            )

            effective_weight = Decimal("0")
            if direct_current:
                selected_record = record
                source_mode = "direct"
                effective_weight = allocation_weight
            elif target_current and link is not None:
                selected_record = target_record
                source_mode = "target_etf"
                effective_weight = (
                    allocation_weight * link.target_allocation_ratio
                )
            elif link is not None and target_record is not None:
                selected_record = target_record
                source_mode = "target_etf"
            elif record is not None:
                selected_record = record
                source_mode = "direct"
            else:
                selected_record = None
                source_mode = "target_etf" if link is not None else "none"

            if selected_record is None:
                snapshots.append(
                    FundLookthroughSnapshotRead(
                        fund_code=fund_code,
                        fund_name=str(entry["fund_name"]),
                        allocation_weight=allocation_weight,
                        covered_weight=Decimal("0"),
                        report_date=None,
                        report_period=None,
                        age_days=None,
                        holding_count=0,
                        status="missing",
                        source_mode=source_mode,
                        target_fund_code=(
                            link.target_fund_code if link is not None else None
                        ),
                        target_fund_name=(
                            link.target_fund_name if link is not None else None
                        ),
                        target_allocation_ratio=(
                            link.target_allocation_ratio
                            if link is not None
                            else None
                        ),
                        relation_report_date=(
                            link.report_date if link is not None else None
                        ),
                    )
                )
                continue
            age_days = (as_of_date - selected_record.report_date).days
            selected_current = direct_current or target_current
            snapshots.append(
                FundLookthroughSnapshotRead(
                    fund_code=fund_code,
                    fund_name=str(entry["fund_name"]),
                    allocation_weight=allocation_weight,
                    covered_weight=effective_weight,
                    report_date=selected_record.report_date,
                    report_period=selected_record.report_period,
                    age_days=(
                        max(age_days, link_age_days or 0)
                        if source_mode == "target_etf"
                        else age_days
                    ),
                    holding_count=len(selected_record.holdings),
                    status="current" if selected_current else "stale",
                    source_mode=source_mode,
                    target_fund_code=(
                        link.target_fund_code if source_mode == "target_etf" else None
                    ),
                    target_fund_name=(
                        link.target_fund_name if source_mode == "target_etf" else None
                    ),
                    target_allocation_ratio=(
                        link.target_allocation_ratio
                        if source_mode == "target_etf"
                        else None
                    ),
                    relation_report_date=(
                        link.report_date if source_mode == "target_etf" else None
                    ),
                )
            )
            if not selected_current:
                continue
            domain_disclosures.append(
                LookthroughFundDisclosure(
                    fund_code=fund_code,
                    allocation_weight=effective_weight,
                    report_date=(
                        min(selected_record.report_date, link.report_date)
                        if source_mode == "target_etf" and link is not None
                        else selected_record.report_date
                    ),
                    holdings=[
                        LookthroughHolding(
                            asset_code=holding.asset_code,
                            asset_name=holding.asset_name,
                            nav_ratio=holding.nav_ratio,
                        )
                        for holding in selected_record.holdings
                    ],
                )
            )

        metrics = calculate_lookthrough(
            domain_disclosures,
            as_of_date=as_of_date,
            stale_after_days=bounded_stale_days,
        )
        snapshots.sort(
            key=lambda item: (-item.allocation_weight, item.fund_code)
        )
        return FundLookthroughRead(
            as_of_date=as_of_date,
            stale_after_days=bounded_stale_days,
            fund_count=len(grouped),
            current_disclosure_count=len(metrics.included_fund_codes),
            coverage_weight=metrics.coverage_weight,
            disclosed_weight=metrics.disclosed_weight,
            assets=[
                FundLookthroughAssetRead(
                    asset_code=item.asset_code,
                    asset_name=item.asset_name,
                    portfolio_weight=item.portfolio_weight,
                    fund_count=item.fund_count,
                )
                for item in metrics.assets[:30]
            ],
            snapshots=snapshots,
            warning=(
                "穿透结果使用基金公开披露的前十大股票；ETF 联接基金在直接股票披露失效时，"
                "按母基金披露的目标 ETF 占比进行二级推导。结果不是实时持仓，不包含现金、"
                "期货和未披露资产；任一层数据过期时都不会纳入聚合。"
            ),
        )

    @staticmethod
    def _is_current_disclosure(
        record: FundDisclosureModel | None,
        *,
        as_of_date: date,
        stale_after_days: int,
    ) -> bool:
        if record is None:
            return False
        age_days = (as_of_date - record.report_date).days
        return 0 <= age_days <= stale_after_days

    def _fetch_holding_disclosure(
        self,
        fund_code: str,
    ) -> FundHoldingsDisclosure:
        source = (
            self.holdings_source
            or self._build_default_holdings_source()
        )
        return source.fetch_latest(fund_code)

    def get_watchlist_summary(self) -> FundWatchlistSummaryRead:
        items = self.repository.list_watchlist_items()
        return FundWatchlistSummaryRead(
            item_count=len(items),
            fund_count=len({item.fund_id for item in items}),
            high_priority_count=len([item for item in items if item.priority <= 2]),
            statuses=sorted({item.status for item in items}),
            risk_levels=sorted({item.risk_level for item in items}),
        )

    def get_nav_summary(self) -> FundNavSummaryRead:
        record_count, fund_count, latest_nav_date, sources = (
            self.repository.get_nav_summary_data()
        )
        return FundNavSummaryRead(
            record_count=record_count,
            fund_count=fund_count,
            latest_nav_date=latest_nav_date,
            sources=sources,
        )

    def get_daily_report(self) -> FundDailyReportRead:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        holding_summary = self.get_holding_summary()
        allocation = self.get_allocation()
        holding_risk = self.get_holding_risk(limit=365)
        watchlist_summary = self.get_watchlist_summary()
        nav_summary = self.get_nav_summary()
        transaction_summary = self.get_transaction_summary()
        nav_age_days = (
            (now.date() - nav_summary.latest_nav_date).days
            if nav_summary.latest_nav_date is not None
            else None
        )
        valuation_complete = (
            holding_summary.position_count > 0
            and allocation.cost_fallback_count == 0
        )
        alerts: list[FundDailyAlertRead] = []

        if holding_summary.position_count == 0:
            alerts.append(
                FundDailyAlertRead(
                    code="no_positions",
                    level="info",
                    message="还没有录入持仓，日报暂时只能展示数据准备情况。",
                )
            )
        elif allocation.cost_fallback_count:
            alerts.append(
                FundDailyAlertRead(
                    code="valuation_incomplete",
                    level="warning",
                    message=(
                        f"{allocation.cost_fallback_count} 条持仓缺少当前净值，"
                        "配置金额暂按成本估算。"
                    ),
                )
            )

        if nav_summary.latest_nav_date is None:
            alerts.append(
                FundDailyAlertRead(
                    code="nav_missing",
                    level="warning",
                    message="数据库里还没有基金净值，收益和估值无法核对。",
                )
            )
        elif nav_age_days is not None and nav_age_days > 5:
            alerts.append(
                FundDailyAlertRead(
                    code="nav_stale",
                    level="warning",
                    message=f"最新净值距今天已有 {nav_age_days} 个自然日，请先同步数据。",
                )
            )

        if (
            allocation.top_holding_weight is not None
            and allocation.top_holding_weight >= Decimal("0.4")
        ):
            alerts.append(
                FundDailyAlertRead(
                    code="holding_concentration",
                    level="info",
                    message=(
                        "最大单一基金占比达到 "
                        f"{allocation.top_holding_weight * 100:.2f}%，"
                        "请结合自己的配置目标判断是否过于集中。"
                    ),
                )
            )

        if (
            holding_risk.fund_count > 0
            and holding_risk.analyzed_fund_count < holding_risk.fund_count
        ):
            missing_count = (
                holding_risk.fund_count - holding_risk.analyzed_fund_count
            )
            alerts.append(
                FundDailyAlertRead(
                    code="risk_history_incomplete",
                    level="info",
                    message=(
                        f"{missing_count} 只持仓基金的历史净值样本不足，"
                        "风险摘要暂时不能完整比较。"
                    ),
                )
            )

        if watchlist_summary.item_count == 0:
            alerts.append(
                FundDailyAlertRead(
                    code="watchlist_empty",
                    level="info",
                    message="观察池为空，暂时没有需要跟踪的候选基金。",
                )
            )

        analysis_context = self._build_daily_analysis_context(
            report_date=now.date(),
            holding_summary=holding_summary,
            allocation=allocation,
            holding_risk=holding_risk,
            nav_summary=nav_summary,
            nav_age_days=nav_age_days,
            valuation_complete=valuation_complete,
            alerts=alerts,
        )
        return FundDailyReportRead(
            report_date=now.date(),
            generated_at=now,
            holding_summary=holding_summary,
            allocation=allocation,
            holding_risk=holding_risk,
            watchlist_summary=watchlist_summary,
            nav_summary=nav_summary,
            transaction_summary=transaction_summary,
            valuation_complete=valuation_complete,
            nav_age_days=nav_age_days,
            alerts=alerts,
            analysis_context=analysis_context,
        )

    def save_daily_report_snapshot(
        self,
        report: FundDailyReportRead | None = None,
    ) -> FundDailySnapshotRead:
        current_report = report or self.get_daily_report()
        quality = current_report.analysis_context.data_quality
        snapshot = self.repository.upsert_daily_report_snapshot(
            report_date=current_report.report_date,
            generated_at=current_report.generated_at,
            contract_version=current_report.analysis_context.contract_version,
            quality_level=quality.level,
            position_count=current_report.holding_summary.position_count,
            fund_count=current_report.holding_summary.fund_count,
            total_cost=current_report.holding_summary.total_cost,
            current_value=current_report.holding_summary.current_value,
            unrealized_profit=current_report.holding_summary.unrealized_profit,
            unrealized_return_rate=(
                current_report.holding_summary.unrealized_return_rate
            ),
            valuation_complete=current_report.valuation_complete,
            latest_nav_date=current_report.nav_summary.latest_nav_date,
            nav_age_days=current_report.nav_age_days,
            risk_fund_count=quality.risk_fund_count,
            risk_covered_fund_count=quality.risk_covered_fund_count,
            risk_sample_count=quality.risk_sample_count,
            top_holding_weight=current_report.allocation.top_holding_weight,
            concentration_hhi=current_report.allocation.concentration_hhi,
            target_configured_count=quality.target_configured_count,
            target_configuration_complete=quality.target_configuration_complete,
            target_weight_total=quality.target_weight_total,
            alert_count=len(current_report.alerts),
            warning_count=len(
                [alert for alert in current_report.alerts if alert.level == "warning"]
            ),
            context_json=current_report.analysis_context.model_dump_json(),
        )
        self.repository.commit()
        snapshots = self.repository.list_daily_report_snapshots(limit=2)
        previous = snapshots[1] if len(snapshots) > 1 else None
        return self._to_daily_snapshot_read(snapshot, previous=previous)

    def get_daily_report_snapshot_history(
        self,
        *,
        limit: int = 30,
    ) -> FundDailySnapshotHistoryRead:
        bounded_limit = max(1, min(limit, 365))
        records = self.repository.list_daily_report_snapshots(
            limit=bounded_limit + 1
        )
        items = [
            self._to_daily_snapshot_read(
                record,
                previous=records[index + 1]
                if index + 1 < len(records)
                else None,
            )
            for index, record in enumerate(records[:bounded_limit])
        ]
        return FundDailySnapshotHistoryRead(count=len(items), items=items)

    def get_daily_report_snapshot_detail(
        self,
        snapshot_id: int,
    ) -> FundDailySnapshotDetailRead:
        records = self.repository.list_daily_report_snapshots(limit=366)
        index = next(
            (index for index, record in enumerate(records) if record.id == snapshot_id),
            None,
        )
        if index is None:
            raise AppError(
                code=ErrorCode.not_found,
                message="Fund daily report snapshot was not found.",
                status_code=404,
            )
        record = records[index]
        summary = self._to_daily_snapshot_read(
            record,
            previous=records[index + 1] if index + 1 < len(records) else None,
        )
        return FundDailySnapshotDetailRead(
            **summary.model_dump(),
            analysis_context=FundDailyAnalysisContextRead.model_validate_json(
                record.context_json
            ),
        )

    def save_daily_ai_summary(
        self,
        snapshot_id: int,
        summary: FundDailyAiSummaryRead,
    ) -> FundDailyAiSummaryArchiveRead:
        record = self.repository.upsert_daily_ai_summary(
            snapshot_id=snapshot_id,
            report_date=summary.report_date,
            generated_at=summary.generated_at,
            contract_version=summary.contract_version,
            provider=summary.provider,
            source_contract=summary.source_contract,
            summary=summary.summary,
            disclaimer=summary.disclaimer,
            model_name=summary.model_name,
            prompt_version=summary.prompt_version,
            input_tokens=summary.input_tokens,
            output_tokens=summary.output_tokens,
            cost=summary.cost,
        )
        self.repository.commit()
        return FundDailyAiSummaryArchiveRead(
            snapshot_id=record.snapshot_id,
            contract_version=record.contract_version,
            generated_at=record.generated_at,
            report_date=record.report_date,
            provider=record.provider,
            source_contract=record.source_contract,
            summary=record.summary,
            disclaimer=record.disclaimer,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cost=record.cost,
        )

    def get_daily_ai_summary(
        self,
        snapshot_id: int,
    ) -> FundDailyAiSummaryArchiveRead | None:
        record = self.repository.get_daily_ai_summary(snapshot_id)
        if record is None:
            return None
        return FundDailyAiSummaryArchiveRead(
            snapshot_id=record.snapshot_id,
            contract_version=record.contract_version,
            generated_at=record.generated_at,
            report_date=record.report_date,
            provider=record.provider,
            source_contract=record.source_contract,
            summary=record.summary,
            disclaimer=record.disclaimer,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cost=record.cost,
        )

    def get_ai_automation_run(self) -> FundAiAutomationRunRead | None:
        report = self.get_daily_report()
        record = self.repository.get_ai_automation_run(report_date=report.report_date)
        if record is None:
            return None
        return FundAiAutomationRunRead(
            id=record.id,
            scope_key=record.scope_key,
            report_date=record.report_date,
            latest_nav_date=record.latest_nav_date,
            summary_id=record.summary_id,
            summary_version=record.summary_version,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cost=record.cost,
            ai_status=record.ai_status,
            push_status=record.push_status,
            ai_error_message=record.ai_error_message,
            push_error_message=record.push_error_message,
            attempts=record.attempts,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def export_daily_report_snapshots_csv(self, *, limit: int = 365) -> str:
        """Return saved daily report snapshots as a portable CSV document."""
        bounded_limit = max(1, min(limit, 365))
        records = self.repository.list_daily_report_snapshots(limit=bounded_limit)
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        fields = [
            "report_date", "generated_at", "quality_level", "position_count",
            "fund_count", "total_cost", "current_value", "unrealized_profit",
            "unrealized_return_rate", "valuation_complete", "latest_nav_date",
            "nav_age_days", "risk_fund_count", "risk_covered_fund_count",
            "risk_sample_count", "top_holding_weight", "concentration_hhi",
            "target_configured_count", "target_configuration_complete",
            "target_weight_total", "alert_count", "warning_count",
        ]
        writer.writerow(fields)
        for record in records:
            writer.writerow([getattr(record, field) for field in fields])
        return output.getvalue()

    def get_daily_report_insights(self) -> FundDailyInsightsRead:
        records = self.repository.list_daily_report_snapshots(limit=366)
        calculated = calculate_daily_insights(
            [
                DailyInsightSnapshot(
                    report_date=record.report_date,
                    position_count=record.position_count,
                    current_value=record.current_value,
                    unrealized_profit=record.unrealized_profit,
                    unrealized_return_rate=record.unrealized_return_rate,
                    concentration_hhi=record.concentration_hhi,
                    quality_level=record.quality_level,
                    nav_age_days=record.nav_age_days,
                )
                for record in records
            ]
        )
        return FundDailyInsightsRead(
            contract_version="fund-daily-insights.v1",
            generated_at=datetime.now(ZoneInfo("Asia/Shanghai")),
            snapshot_count=calculated.snapshot_count,
            latest_date=calculated.latest_date,
            comparisons=[
                FundDailyPeriodComparisonRead(
                    period_days=comparison.period_days,
                    status=comparison.status,
                    latest_date=comparison.latest_date,
                    baseline_date=comparison.baseline_date,
                    sample_count=comparison.sample_count,
                    observed_span_days=comparison.observed_span_days,
                    change=(
                        FundDailySnapshotChangeRead(
                            position_count=comparison.position_count_change or 0,
                            current_value=comparison.current_value_change,
                            unrealized_profit=comparison.unrealized_profit_change,
                            unrealized_return_rate=(
                                comparison.unrealized_return_rate_change
                            ),
                            concentration_hhi=comparison.concentration_hhi_change,
                        )
                        if comparison.status == "available"
                        else None
                    ),
                    explanation=comparison.explanation,
                )
                for comparison in calculated.comparisons
            ],
            alerts=[
                FundDailyInsightAlertRead(
                    code=alert.code,
                    level=alert.level,
                    message=alert.message,
                    sample_scope=alert.sample_scope,
                )
                for alert in calculated.alerts
            ],
            disclaimers=[
                "变化基于已保存日报快照，不等同于连续实时行情。",
                "估值变化可能同时包含市场波动、申赎和持仓编辑影响。",
                "异常提醒用于数据核对和风险观察，不构成投资建议。",
            ],
        )

    def get_daily_report_ai_input(self) -> FundDailyAiInputRead:
        report = self.get_daily_report()
        insights = self.get_daily_report_insights()
        return FundDailyAiInputRead(
            contract_version="fund-daily-ai-input.v1",
            generated_at=datetime.now(ZoneInfo("Asia/Shanghai")),
            report_date=report.report_date,
            source_contracts=[
                report.analysis_context.contract_version,
                insights.contract_version,
            ],
            data_quality=report.analysis_context.data_quality,
            facts=report.analysis_context.facts,
            insights=insights,
            summarization_rules=[
                "只总结输入中已经提供的事实和变化，不补造实时行情。",
                "所有趋势结论必须同时说明比较区间和样本数量。",
                "样本不足时明确说明不足，不推断未来表现。",
                "区分市场波动、申赎和持仓编辑可能造成的估值变化。",
                "不使用保证收益、推荐买卖或提高收益率等表述。",
            ],
            disclaimers=list(
                dict.fromkeys(
                    [
                        *report.analysis_context.disclaimers,
                        *insights.disclaimers,
                    ]
                )
            ),
        )

    @classmethod
    def _to_daily_snapshot_read(
        cls,
        snapshot: FundDailyReportSnapshotModel,
        *,
        previous: FundDailyReportSnapshotModel | None,
    ) -> FundDailySnapshotRead:
        change = None
        if previous is not None:
            change = FundDailySnapshotChangeRead(
                position_count=snapshot.position_count - previous.position_count,
                current_value=cls._optional_decimal_change(
                    snapshot.current_value,
                    previous.current_value,
                ),
                unrealized_profit=cls._optional_decimal_change(
                    snapshot.unrealized_profit,
                    previous.unrealized_profit,
                ),
                unrealized_return_rate=cls._optional_decimal_change(
                    snapshot.unrealized_return_rate,
                    previous.unrealized_return_rate,
                ),
                concentration_hhi=cls._optional_decimal_change(
                    snapshot.concentration_hhi,
                    previous.concentration_hhi,
                ),
            )
        return FundDailySnapshotRead(
            id=snapshot.id,
            report_date=snapshot.report_date,
            generated_at=snapshot.generated_at,
            contract_version=snapshot.contract_version,
            quality_level=snapshot.quality_level,
            position_count=snapshot.position_count,
            fund_count=snapshot.fund_count,
            total_cost=snapshot.total_cost,
            current_value=snapshot.current_value,
            unrealized_profit=snapshot.unrealized_profit,
            unrealized_return_rate=snapshot.unrealized_return_rate,
            valuation_complete=snapshot.valuation_complete,
            latest_nav_date=snapshot.latest_nav_date,
            nav_age_days=snapshot.nav_age_days,
            risk_fund_count=snapshot.risk_fund_count,
            risk_covered_fund_count=snapshot.risk_covered_fund_count,
            risk_sample_count=snapshot.risk_sample_count,
            top_holding_weight=snapshot.top_holding_weight,
            concentration_hhi=snapshot.concentration_hhi,
            target_configured_count=snapshot.target_configured_count,
            target_configuration_complete=snapshot.target_configuration_complete,
            target_weight_total=snapshot.target_weight_total,
            alert_count=snapshot.alert_count,
            warning_count=snapshot.warning_count,
            change_from_previous=change,
        )

    @staticmethod
    def _optional_decimal_change(
        current: Decimal | None,
        previous: Decimal | None,
    ) -> Decimal | None:
        if current is None or previous is None:
            return None
        return current - previous

    @staticmethod
    def _build_daily_analysis_context(
        *,
        report_date: date,
        holding_summary: FundHoldingSummaryRead,
        allocation: FundAllocationRead,
        holding_risk: FundHoldingRiskRead,
        nav_summary: FundNavSummaryRead,
        nav_age_days: int | None,
        valuation_complete: bool,
        alerts: list[FundDailyAlertRead],
    ) -> FundDailyAnalysisContextRead:
        risk_sample_count = sum(item.sample_count for item in holding_risk.items)
        quality_warnings = [
            alert.message
            for alert in alerts
            if alert.code
            in {
                "no_positions",
                "valuation_incomplete",
                "nav_missing",
                "nav_stale",
                "risk_history_incomplete",
            }
        ]
        if holding_summary.position_count == 0:
            quality_level = "insufficient"
        elif (
            valuation_complete
            and nav_summary.latest_nav_date is not None
            and (nav_age_days is None or nav_age_days <= 5)
            and holding_risk.analyzed_fund_count == holding_risk.fund_count
        ):
            quality_level = "complete"
        else:
            quality_level = "partial"

        facts = [
            FundDailyFactRead(
                code="valuation_coverage",
                category="data_quality",
                label="持仓估值覆盖",
                value=(
                    f"{holding_summary.valued_position_count}/"
                    f"{holding_summary.position_count}"
                ),
                unit="条持仓",
                sample_scope=f"截至 {report_date} 的当前持仓",
                severity="info" if valuation_complete else "warning",
            ),
            FundDailyFactRead(
                code="risk_coverage",
                category="data_quality",
                label="风险样本覆盖",
                value=(
                    f"{holding_risk.analyzed_fund_count}/"
                    f"{holding_risk.fund_count}"
                ),
                unit="只基金",
                sample_scope=(
                    f"每只最多 {holding_risk.sample_limit} 个净值样本，"
                    f"合计 {risk_sample_count} 个"
                ),
                severity=(
                    "info"
                    if holding_risk.fund_count > 0
                    and holding_risk.analyzed_fund_count == holding_risk.fund_count
                    else "warning"
                ),
            ),
            FundDailyFactRead(
                code="target_configuration",
                category="allocation",
                label="目标配置覆盖",
                value=(
                    f"{allocation.configured_target_count}/"
                    f"{allocation.position_count}"
                ),
                unit="条持仓",
                sample_scope=(
                    f"目标占比合计 {allocation.target_weight_total * 100:.2f}%"
                ),
                severity=(
                    "info" if allocation.target_configuration_complete else "warning"
                ),
            ),
        ]
        if holding_summary.unrealized_return_rate is not None:
            facts.append(
                FundDailyFactRead(
                    code="unrealized_return_rate",
                    category="performance",
                    label="持仓浮动收益率",
                    value=f"{holding_summary.unrealized_return_rate * 100:.2f}",
                    unit="%",
                    sample_scope=(
                        f"有净值的 {holding_summary.valued_position_count} 条持仓"
                    ),
                    severity="info",
                )
            )
        if allocation.concentration_hhi is not None:
            facts.append(
                FundDailyFactRead(
                    code="allocation_hhi",
                    category="allocation",
                    label="持仓集中度 HHI",
                    value=f"{allocation.concentration_hhi:.4f}",
                    unit="指数",
                    sample_scope=f"{allocation.position_count} 条当前持仓",
                    severity="info",
                )
            )

        risk_items = [
            item for item in holding_risk.items if item.calculation_available
        ]
        if risk_items:
            deepest_drawdown = min(
                risk_items,
                key=lambda item: item.maximum_drawdown or Decimal("0"),
            )
            facts.append(
                FundDailyFactRead(
                    code="deepest_fund_drawdown",
                    category="risk",
                    label="样本内最大基金回撤",
                    value=f"{(deepest_drawdown.maximum_drawdown or Decimal('0')) * 100:.2f}",
                    unit="%",
                    sample_scope=(
                        f"{deepest_drawdown.fund_name}，"
                        f"{deepest_drawdown.start_date or '--'} 至 "
                        f"{deepest_drawdown.end_date or '--'}，"
                        f"{deepest_drawdown.sample_count} 个样本"
                    ),
                    severity="info",
                )
            )

        return FundDailyAnalysisContextRead(
            contract_version="fund-daily-context.v1",
            report_date=report_date,
            data_quality=FundDailyDataQualityRead(
                level=quality_level,
                position_count=holding_summary.position_count,
                valued_position_count=holding_summary.valued_position_count,
                latest_nav_date=nav_summary.latest_nav_date,
                nav_age_days=nav_age_days,
                risk_fund_count=holding_risk.fund_count,
                risk_covered_fund_count=holding_risk.analyzed_fund_count,
                risk_sample_count=risk_sample_count,
                target_configured_count=allocation.configured_target_count,
                target_configuration_complete=(
                    allocation.target_configuration_complete
                ),
                target_weight_total=allocation.target_weight_total,
                warnings=quality_warnings,
            ),
            facts=facts,
            disclaimers=[
                "数据来自 HAP 已保存记录，不代表实时行情。",
                "风险指标仅描述历史样本，不代表未来表现。",
                "结构化摘要用于数据分析，不构成投资建议。",
            ],
        )

    def _to_nav_record_read(self, record: FundNavRecordModel) -> FundNavRecordRead:
        fund: FundModel = record.fund
        return FundNavRecordRead(
            id=record.id,
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            fund_type=fund.fund_type,
            nav_date=record.nav_date,
            unit_nav=record.unit_nav,
            accumulated_nav=record.accumulated_nav,
            source=record.source,
            note=record.note,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_target_link(record: FundTargetLinkModel) -> TargetFundLink:
        return TargetFundLink(
            parent_fund_code=record.parent_fund_code,
            target_fund_code=record.target_fund_code,
            target_fund_name=record.target_fund_name,
            target_allocation_ratio=record.target_allocation_ratio,
            report_date=record.report_date,
            source_url=record.source_url,
        )

    @staticmethod
    def _to_target_link_read(
        link: TargetFundLink,
        *,
        origin: str,
    ) -> FundTargetLinkRead:
        return FundTargetLinkRead(
            parent_fund_code=link.parent_fund_code,
            target_fund_code=link.target_fund_code,
            target_fund_name=link.target_fund_name,
            target_allocation_ratio=link.target_allocation_ratio,
            report_date=link.report_date,
            source_url=link.source_url,
            origin=origin,
        )

    def _to_watchlist_read(self, item: FundWatchlistItemModel) -> FundWatchlistRead:
        fund: FundModel = item.fund
        return FundWatchlistRead(
            id=item.id,
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            fund_type=fund.fund_type,
            priority=item.priority,
            status=item.status,
            watch_reason=item.watch_reason,
            risk_level=item.risk_level,
            target_position=item.target_position,
            tags=item.tags,
            note=item.note,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _to_position_read(self, position: FundPositionModel) -> FundPositionRead:
        fund: FundModel = position.fund
        current_value = (
            position.shares * position.current_nav
            if position.current_nav is not None
            else None
        )
        unrealized_profit = (
            current_value - position.total_cost
            if current_value is not None
            else None
        )
        unrealized_return_rate = (
            unrealized_profit / position.total_cost
            if unrealized_profit is not None and position.total_cost > 0
            else None
        )
        return FundPositionRead(
            id=position.id,
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            fund_type=fund.fund_type,
            account_name=position.account_name,
            shares=position.shares,
            cost_price=position.cost_price,
            total_cost=position.total_cost,
            current_nav=position.current_nav,
            target_weight=position.target_weight,
            current_value=current_value,
            unrealized_profit=unrealized_profit,
            unrealized_return_rate=unrealized_return_rate,
            opened_at=position.opened_at,
            tags=position.tags,
            note=position.note,
            created_at=position.created_at,
            updated_at=position.updated_at,
        )

    def _to_account_snapshot_read(
        self,
        snapshot: FundAccountSnapshotModel,
    ) -> FundAccountSnapshotRead:
        positions = self.repository.list_positions()
        positions_by_code: dict[str, list[FundPositionModel]] = {}
        for position in positions:
            positions_by_code.setdefault(position.fund.code, []).append(position)

        official_codes = {
            holding.asset_code
            for holding in snapshot.holdings
            if holding.asset_type == "fund"
        }
        items: list[FundAccountHoldingRead] = []
        matched_count = 0
        official_only_count = 0
        manual_incomplete_count = 0
        for holding in snapshot.holdings:
            manual_positions = positions_by_code.get(holding.asset_code, [])
            manual_value = self._manual_positions_current_value(manual_positions)
            if not manual_positions:
                comparison_status = "official_only"
                official_only_count += 1
            elif manual_value is None:
                comparison_status = "manual_incomplete"
                manual_incomplete_count += 1
            else:
                comparison_status = "matched"
                matched_count += 1
            items.append(
                FundAccountHoldingRead(
                    id=holding.id,
                    asset_code=holding.asset_code,
                    asset_name=holding.asset_name,
                    asset_type=holding.asset_type,
                    asset_value=holding.asset_value,
                    daily_profit=holding.daily_profit,
                    hold_profit=holding.hold_profit,
                    hold_profit_rate=holding.hold_profit_rate,
                    constant_profit=holding.constant_profit,
                    constant_profit_rate=holding.constant_profit_rate,
                    manual_position_count=len(manual_positions),
                    manual_current_value=manual_value,
                    value_difference=(
                        holding.asset_value - manual_value
                        if manual_value is not None
                        else None
                    ),
                    comparison_status=comparison_status,
                )
            )

        manual_only = [
            FundAccountManualOnlyRead(
                fund_code=fund_code,
                fund_name=fund_positions[0].fund.name,
                position_count=len(fund_positions),
                current_value=self._manual_positions_current_value(fund_positions),
            )
            for fund_code, fund_positions in sorted(positions_by_code.items())
            if fund_code not in official_codes
        ]
        manual_current_value = self._manual_positions_current_value(positions)
        return FundAccountSnapshotRead(
            id=snapshot.id,
            source=snapshot.source,
            account_label=snapshot.account_label,
            contract_version="fund-account-holdings.v1",
            captured_at=snapshot.captured_at,
            holding_count=snapshot.holding_count,
            total_asset_value=snapshot.total_asset_value,
            manual_position_count=len(positions),
            manual_current_value=manual_current_value,
            matched_count=matched_count,
            official_only_count=official_only_count,
            manual_incomplete_count=manual_incomplete_count,
            items=items,
            manual_only=manual_only,
        )

    @staticmethod
    def _manual_positions_current_value(
        positions: list[FundPositionModel],
    ) -> Decimal | None:
        if not positions or any(position.current_nav is None for position in positions):
            return None
        return sum(
            (
                position.shares * position.current_nav
                for position in positions
                if position.current_nav is not None
            ),
            start=Decimal("0"),
        )

    def _to_transaction_read(
        self,
        transaction: FundTransactionModel,
    ) -> FundTransactionRead:
        fund: FundModel = transaction.fund
        return FundTransactionRead(
            id=transaction.id,
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            fund_type=fund.fund_type,
            account_name=transaction.account_name,
            transaction_type=transaction.transaction_type,
            trade_date=transaction.trade_date,
            shares=transaction.shares,
            unit_price=transaction.unit_price,
            amount=transaction.amount,
            fee=transaction.fee,
            cash_flow=self._transaction_cash_flow(transaction),
            note=transaction.note,
            external_source=transaction.external_source,
            external_trade_id=transaction.external_trade_id,
            external_trade_type=transaction.external_trade_type,
            external_business_code=transaction.external_business_code,
            external_status=transaction.external_status,
            external_confirm_status=transaction.external_confirm_status,
            confirm_date=transaction.confirm_date,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )

    @staticmethod
    def _transaction_cash_flow(transaction: FundTransactionModel) -> Decimal:
        if transaction.transaction_type == "buy":
            return -(transaction.amount + transaction.fee)
        if transaction.transaction_type == "sell":
            return transaction.amount - transaction.fee
        if transaction.transaction_type == "dividend":
            return transaction.amount
        return -transaction.amount

    @staticmethod
    def _cash_flow_performance_warning(
        *,
        transaction_count: int,
        invested_cash: Decimal,
        valuation_complete: bool,
    ) -> str:
        if transaction_count == 0:
            return "尚未录入交易流水，暂时无法计算现金流收益。"
        if invested_cash <= 0:
            return "流水中没有有效资金投入，暂时无法计算收益率。"
        if not valuation_complete:
            return "部分持仓缺少当前净值，补齐估值后才能计算现金流收益。"
        return "结果依赖交易流水完整性；若流水从中途开始录入，请勿视为完整历史收益。"

    @staticmethod
    def _build_allocation_groups(
        valued: list[tuple[FundPositionModel, Decimal, str]],
        *,
        total_amount: Decimal,
        group_by: str,
    ) -> list[FundAllocationGroupRead]:
        grouped: dict[str, tuple[Decimal, int]] = {}
        for position, amount, _ in valued:
            label = (
                position.fund.fund_type
                if group_by == "fund_type"
                else position.account_name
            )
            current_amount, count = grouped.get(label, (Decimal("0"), 0))
            grouped[label] = (current_amount + amount, count + 1)
        groups = [
            FundAllocationGroupRead(
                label=label,
                amount=amount,
                weight=amount / total_amount if total_amount > 0 else Decimal("0"),
                position_count=count,
            )
            for label, (amount, count) in grouped.items()
        ]
        return sorted(groups, key=lambda item: (-item.amount, item.label))

    def _build_default_nav_source(self) -> EastmoneyFundNavSource:
        if self.settings is None:
            return EastmoneyFundNavSource()
        return EastmoneyFundNavSource(
            timeout_seconds=self.settings.fund_nav_sync_timeout_seconds,
            url_template=self.settings.fund_eastmoney_pingzhongdata_url,
        )

    def _build_default_holdings_source(
        self,
    ) -> EastmoneyFundHoldingsSource:
        if self.settings is None:
            return EastmoneyFundHoldingsSource()
        return EastmoneyFundHoldingsSource(
            timeout_seconds=self.settings.fund_nav_sync_timeout_seconds,
            url_template=self.settings.fund_eastmoney_holdings_url,
        )
