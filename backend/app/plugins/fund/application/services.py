from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from loguru import logger

from app.core.config.settings import Settings
from app.plugins.fund.domain.holding_correlation import (
    FundCorrelationSeries,
    calculate_holding_correlations,
)
from app.plugins.fund.domain.lookthrough import (
    LookthroughFundDisclosure,
    LookthroughHolding,
    calculate_lookthrough,
)
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
from app.plugins.fund.infrastructure.persistence.models import (
    FundModel,
    FundNavRecordModel,
    FundPositionModel,
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
from app.plugins.fund.interfaces.schemas import (
    FundAllocationGroupRead,
    FundAllocationHoldingRead,
    FundAllocationRead,
    FundCashFlowPerformanceRead,
    FundCorrelationMemberRead,
    FundCorrelationPairRead,
    FundDailyAlertRead,
    FundDailyReportRead,
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
    FundRiskContributionItemRead,
    FundRiskContributionRead,
    FundTrackedNavSyncRead,
    FundTransactionCreate,
    FundTransactionRead,
    FundTransactionSummaryRead,
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
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.nav_source = nav_source
        self.holdings_source = holdings_source

    def list_positions(self) -> list[FundPositionRead]:
        return [self._to_position_read(position) for position in self.repository.list_positions()]

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
        source = self.nav_source or self._build_default_nav_source()
        latest = source.fetch_latest(fund_code=payload.fund_code, fund_type=payload.fund_type)
        return self._persist_latest_nav(latest)

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
        return source.fetch_history(
            fund_code=fund_code,
            fund_type=fund_type,
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
                previous_date = existing[0].nav_date if existing else None
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
        return source.fetch_latest(fund_code=fund_code, fund_type=fund_type)

    def _persist_latest_nav(self, latest: FundLatestNav) -> FundNavRecordRead:
        fund = self.repository.upsert_fund(
            code=latest.fund_code,
            name=latest.fund_name,
            fund_type=latest.fund_type,
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
        source = self.nav_source or self._build_default_nav_source()
        latest = source.fetch_latest(fund_code=payload.fund_code, fund_type=payload.fund_type)
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
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=payload.fund_type,
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
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=payload.fund_type,
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
        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=payload.fund_type,
        )
        position = self.repository.create_position(
            fund=fund,
            account_name=payload.account_name,
            shares=payload.shares,
            cost_price=payload.cost_price,
            total_cost=payload.normalized_total_cost,
            current_nav=payload.current_nav,
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

        fund = self.repository.upsert_fund(
            code=payload.fund_code,
            name=payload.fund_name,
            fund_type=payload.fund_type,
        )
        updated = self.repository.update_position(
            position,
            fund=fund,
            account_name=payload.account_name,
            shares=payload.shares,
            cost_price=payload.cost_price,
            total_cost=payload.normalized_total_cost,
            current_nav=payload.current_nav,
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

        holdings = [
            FundAllocationHoldingRead(
                position_id=position.id,
                fund_code=position.fund.code,
                fund_name=position.fund.name,
                fund_type=position.fund.fund_type,
                account_name=position.account_name,
                amount=amount,
                weight=amount / total_amount if total_amount > 0 else Decimal("0"),
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
        targets_by_code: dict[str, tuple[str, str]] = {}
        for position in self.repository.list_positions():
            targets_by_code[position.fund.code] = (
                position.fund.name,
                position.fund.fund_type,
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

        records = self.repository.list_latest_disclosures(
            fund_ids=[int(entry["fund_id"]) for entry in grouped.values()],
        )
        records_by_fund_id = {record.fund_id: record for record in records}
        domain_disclosures: list[LookthroughFundDisclosure] = []
        snapshots: list[FundLookthroughSnapshotRead] = []
        for fund_code, entry in grouped.items():
            record = records_by_fund_id.get(int(entry["fund_id"]))
            allocation_weight = Decimal(entry["allocation_weight"])
            if record is None:
                snapshots.append(
                    FundLookthroughSnapshotRead(
                        fund_code=fund_code,
                        fund_name=str(entry["fund_name"]),
                        allocation_weight=allocation_weight,
                        report_date=None,
                        report_period=None,
                        age_days=None,
                        holding_count=0,
                        status="missing",
                    )
                )
                continue
            age_days = (as_of_date - record.report_date).days
            status = (
                "current"
                if 0 <= age_days <= bounded_stale_days
                else "stale"
            )
            snapshots.append(
                FundLookthroughSnapshotRead(
                    fund_code=fund_code,
                    fund_name=str(entry["fund_name"]),
                    allocation_weight=allocation_weight,
                    report_date=record.report_date,
                    report_period=record.report_period,
                    age_days=age_days,
                    holding_count=len(record.holdings),
                    status=status,
                )
            )
            domain_disclosures.append(
                LookthroughFundDisclosure(
                    fund_code=fund_code,
                    allocation_weight=allocation_weight,
                    report_date=record.report_date,
                    holdings=[
                        LookthroughHolding(
                            asset_code=holding.asset_code,
                            asset_name=holding.asset_name,
                            nav_ratio=holding.nav_ratio,
                        )
                        for holding in record.holdings
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
                "穿透结果使用基金最近一次公开披露的前十大股票，并按当前基金仓位加权。"
                "它不是实时持仓，也不包含未披露资产；超过设定天数的旧快照不会纳入聚合。"
                "ETF 联接和 QDII 的目标基金二级穿透将在后续版本补充。"
            ),
        )

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
            current_value=current_value,
            unrealized_profit=unrealized_profit,
            unrealized_return_rate=unrealized_return_rate,
            opened_at=position.opened_at,
            tags=position.tags,
            note=position.note,
            created_at=position.created_at,
            updated_at=position.updated_at,
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
