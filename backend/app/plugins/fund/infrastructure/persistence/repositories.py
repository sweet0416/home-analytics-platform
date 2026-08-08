from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.time import utcnow
from app.plugins.fund.infrastructure.persistence.models import (
    FundAccountHoldingSnapshotModel,
    FundAccountSnapshotModel,
    FundAiAutomationRunModel,
    FundDailyAiSummaryModel,
    FundDailyReportSnapshotModel,
    FundDisclosureHoldingModel,
    FundDisclosureModel,
    FundModel,
    FundNavRecordModel,
    FundNavSyncRunModel,
    FundPositionModel,
    FundTargetLinkModel,
    FundTransactionModel,
    FundWatchlistItemModel,
)


class FundRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def claim_ai_automation_run(
        self,
        *,
        report_date: date,
        latest_nav_date: date | None,
        nav_fingerprint: str,
        summary_version: str,
        model_name: str,
        prompt_version: str,
        scope_key: str = "portfolio",
    ) -> FundAiAutomationRunModel | None:
        """Atomically reserve the daily automatic-summary slot.

        A unique database index is the source of truth, so concurrent workers
        cannot both reserve the same daily slot.
        """
        run = FundAiAutomationRunModel(
            scope_key=scope_key,
            report_date=report_date,
            latest_nav_date=latest_nav_date,
            nav_fingerprint=nav_fingerprint,
            summary_version=summary_version,
            model_name=model_name,
            prompt_version=prompt_version,
            ai_status="PENDING",
            push_status="NOT_REQUESTED",
            attempts=0,
        )
        try:
            with self.db.begin_nested():
                self.db.add(run)
                self.db.flush()
        except IntegrityError:
            return None
        return run

    def get_ai_automation_run(
        self,
        *,
        report_date: date,
        scope_key: str = "portfolio",
    ) -> FundAiAutomationRunModel | None:
        return self.db.scalar(
            select(FundAiAutomationRunModel).where(
                FundAiAutomationRunModel.report_date == report_date,
                FundAiAutomationRunModel.scope_key == scope_key,
            )
        )

    def create_account_snapshot(
        self,
        *,
        source: str,
        account_label: str,
        contract_version: str,
        captured_at: datetime,
        holdings: list[
            tuple[
                str,
                str,
                str,
                Decimal,
                Decimal | None,
                Decimal | None,
                Decimal | None,
                Decimal | None,
                Decimal | None,
            ]
        ],
    ) -> FundAccountSnapshotModel:
        snapshot = FundAccountSnapshotModel(
            source=source,
            account_label=account_label,
            contract_version=contract_version,
            captured_at=captured_at,
            holding_count=len(holdings),
            total_asset_value=sum(
                (holding[3] for holding in holdings),
                start=Decimal("0"),
            ),
        )
        snapshot.holdings = [
            FundAccountHoldingSnapshotModel(
                asset_code=asset_code,
                asset_name=asset_name,
                asset_type=asset_type,
                asset_value=asset_value,
                daily_profit=daily_profit,
                hold_profit=hold_profit,
                hold_profit_rate=hold_profit_rate,
                constant_profit=constant_profit,
                constant_profit_rate=constant_profit_rate,
            )
            for (
                asset_code,
                asset_name,
                asset_type,
                asset_value,
                daily_profit,
                hold_profit,
                hold_profit_rate,
                constant_profit,
                constant_profit_rate,
            ) in holdings
        ]
        self.db.add(snapshot)
        self.db.flush()
        return snapshot

    def get_latest_account_snapshot(self) -> FundAccountSnapshotModel | None:
        return self.db.scalar(
            select(FundAccountSnapshotModel)
            .options(selectinload(FundAccountSnapshotModel.holdings))
            .order_by(
                FundAccountSnapshotModel.captured_at.desc(),
                FundAccountSnapshotModel.id.desc(),
            )
        )

    def create_nav_sync_run(
        self,
        *,
        trigger_type: str,
        status: str,
        started_at: datetime,
        finished_at: datetime,
        total: int,
        succeeded: int,
        failed: int,
        updated: int,
        skipped: bool,
        message: str,
    ) -> FundNavSyncRunModel:
        run = FundNavSyncRunModel(
            trigger_type=trigger_type,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            total=total,
            succeeded=succeeded,
            failed=failed,
            updated=updated,
            skipped=skipped,
            message=message,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get_latest_nav_sync_run(self) -> FundNavSyncRunModel | None:
        return self.db.scalar(
            select(FundNavSyncRunModel).order_by(
                FundNavSyncRunModel.finished_at.desc(),
                FundNavSyncRunModel.id.desc(),
            )
        )

    def get_latest_updated_nav_sync_run(self) -> FundNavSyncRunModel | None:
        return self.db.scalar(
            select(FundNavSyncRunModel)
            .where(FundNavSyncRunModel.updated > 0)
            .order_by(
                FundNavSyncRunModel.finished_at.desc(),
                FundNavSyncRunModel.id.desc(),
            )
        )

    def upsert_daily_report_snapshot(
        self,
        **values: object,
    ) -> FundDailyReportSnapshotModel:
        report_date = values["report_date"]
        snapshot = self.db.scalar(
            select(FundDailyReportSnapshotModel).where(
                FundDailyReportSnapshotModel.report_date == report_date
            )
        )
        if snapshot is None:
            snapshot = FundDailyReportSnapshotModel(**values)
            self.db.add(snapshot)
        else:
            for field, value in values.items():
                setattr(snapshot, field, value)
            snapshot.updated_at = utcnow()
        self.db.flush()
        return snapshot

    def list_daily_report_snapshots(
        self,
        *,
        limit: int,
    ) -> list[FundDailyReportSnapshotModel]:
        return list(
            self.db.scalars(
                select(FundDailyReportSnapshotModel)
                .order_by(
                    FundDailyReportSnapshotModel.report_date.desc(),
                    FundDailyReportSnapshotModel.id.desc(),
                )
                .limit(limit)
            )
        )

    def get_daily_report_snapshot(
        self,
        snapshot_id: int,
    ) -> FundDailyReportSnapshotModel | None:
        return self.db.scalar(
            select(FundDailyReportSnapshotModel).where(
                FundDailyReportSnapshotModel.id == snapshot_id
            )
        )

    def upsert_daily_ai_summary(
        self,
        *,
        snapshot_id: int,
        report_date: date,
        generated_at: datetime,
        contract_version: str,
        provider: str,
        source_contract: str,
        summary: str,
        disclaimer: str,
        model_name: str = "",
        prompt_version: str = "fund-daily-prompt.v1",
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost: Decimal | None = None,
    ) -> FundDailyAiSummaryModel:
        record = self.db.scalar(
            select(FundDailyAiSummaryModel).where(
                FundDailyAiSummaryModel.snapshot_id == snapshot_id,
                FundDailyAiSummaryModel.provider == provider,
            )
        )
        values = {
            "snapshot_id": snapshot_id,
            "report_date": report_date,
            "generated_at": generated_at,
            "contract_version": contract_version,
            "provider": provider,
            "source_contract": source_contract,
            "summary": summary,
            "disclaimer": disclaimer,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
        }
        if record is None:
            record = FundDailyAiSummaryModel(**values)
            self.db.add(record)
        else:
            for field, value in values.items():
                setattr(record, field, value)
            record.updated_at = utcnow()
        self.db.flush()
        return record

    def get_daily_ai_summary(self, snapshot_id: int) -> FundDailyAiSummaryModel | None:
        return self.db.scalar(
            select(FundDailyAiSummaryModel).where(
                FundDailyAiSummaryModel.snapshot_id == snapshot_id
            )
        )

    def get_fund_by_code(self, code: str) -> FundModel | None:
        return self.db.scalar(select(FundModel).where(FundModel.code == code))

    def list_target_links(self) -> list[FundTargetLinkModel]:
        return list(
            self.db.scalars(
                select(FundTargetLinkModel).order_by(
                    FundTargetLinkModel.parent_fund_code
                )
            )
        )

    def get_target_link(
        self,
        parent_fund_code: str,
    ) -> FundTargetLinkModel | None:
        return self.db.scalar(
            select(FundTargetLinkModel).where(
                FundTargetLinkModel.parent_fund_code == parent_fund_code
            )
        )

    def upsert_target_link(
        self,
        *,
        parent_fund_code: str,
        target_fund_code: str,
        target_fund_name: str,
        target_allocation_ratio: Decimal,
        report_date: date,
        source_url: str,
    ) -> FundTargetLinkModel:
        link = self.get_target_link(parent_fund_code)
        now = utcnow()
        if link is None:
            link = FundTargetLinkModel(
                parent_fund_code=parent_fund_code,
                target_fund_code=target_fund_code,
                target_fund_name=target_fund_name,
                target_allocation_ratio=target_allocation_ratio,
                report_date=report_date,
                source_url=source_url,
                enabled=True,
            )
            self.db.add(link)
        else:
            link.target_fund_code = target_fund_code
            link.target_fund_name = target_fund_name
            link.target_allocation_ratio = target_allocation_ratio
            link.report_date = report_date
            link.source_url = source_url
            link.enabled = True
            link.updated_at = now
        self.db.flush()
        return link

    def disable_target_link(self, link: FundTargetLinkModel) -> None:
        link.enabled = False
        link.updated_at = utcnow()
        self.db.flush()

    def upsert_fund(
        self,
        *,
        code: str,
        name: str,
        fund_type: str,
        source: str | None = None,
    ) -> FundModel:
        fund = self.get_fund_by_code(code)
        now = utcnow()
        if fund is not None:
            fund.name = name
            fund.fund_type = fund_type
            if source:
                fund.source = source
            fund.updated_at = now
            self.db.flush()
            return fund

        fund = FundModel(
            code=code,
            name=name,
            fund_type=fund_type,
            source=source or "manual",
        )
        self.db.add(fund)
        self.db.flush()
        return fund

    def create_position(
        self,
        *,
        fund: FundModel,
        account_name: str,
        shares: Decimal,
        cost_price: Decimal,
        total_cost: Decimal,
        current_nav: Decimal | None,
        target_weight: Decimal | None = None,
        opened_at: date | None,
        tags: str,
        note: str,
    ) -> FundPositionModel:
        position = FundPositionModel(
            fund=fund,
            account_name=account_name,
            shares=shares,
            cost_price=cost_price,
            total_cost=total_cost,
            current_nav=current_nav,
            target_weight=target_weight,
            opened_at=opened_at,
            tags=tags,
            note=note,
        )
        self.db.add(position)
        self.db.flush()
        return position

    def get_position(self, position_id: int) -> FundPositionModel | None:
        return self.db.scalar(
            select(FundPositionModel)
            .options(selectinload(FundPositionModel.fund))
            .where(FundPositionModel.id == position_id)
        )

    def update_position(
        self,
        position: FundPositionModel,
        *,
        fund: FundModel,
        account_name: str,
        shares: Decimal,
        cost_price: Decimal,
        total_cost: Decimal,
        current_nav: Decimal | None,
        target_weight: Decimal | None = None,
        opened_at: date | None,
        tags: str,
        note: str,
    ) -> FundPositionModel:
        position.fund = fund
        position.account_name = account_name
        position.shares = shares
        position.cost_price = cost_price
        position.total_cost = total_cost
        position.current_nav = current_nav
        position.target_weight = target_weight
        position.opened_at = opened_at
        position.tags = tags
        position.note = note
        position.updated_at = utcnow()
        self.db.flush()
        return position

    def delete_position(self, position: FundPositionModel) -> None:
        self.db.delete(position)
        self.db.flush()

    def create_transaction(
        self,
        *,
        fund: FundModel,
        account_name: str,
        transaction_type: str,
        trade_date: date,
        shares: Decimal | None,
        unit_price: Decimal | None,
        amount: Decimal,
        fee: Decimal,
        note: str,
    ) -> FundTransactionModel:
        transaction = FundTransactionModel(
            fund=fund,
            account_name=account_name,
            transaction_type=transaction_type,
            trade_date=trade_date,
            shares=shares,
            unit_price=unit_price,
            amount=amount,
            fee=fee,
            note=note,
        )
        self.db.add(transaction)
        self.db.flush()
        return transaction

    def get_transaction(self, transaction_id: int) -> FundTransactionModel | None:
        return self.db.scalar(
            select(FundTransactionModel)
            .options(selectinload(FundTransactionModel.fund))
            .where(FundTransactionModel.id == transaction_id)
        )

    def delete_transaction(self, transaction: FundTransactionModel) -> None:
        self.db.delete(transaction)
        self.db.flush()

    def list_transactions(self, limit: int | None = 100) -> list[FundTransactionModel]:
        statement = (
            select(FundTransactionModel)
            .options(selectinload(FundTransactionModel.fund))
            .order_by(
                FundTransactionModel.trade_date.desc(),
                FundTransactionModel.id.desc(),
            )
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.scalars(statement))

    def create_watchlist_item(
        self,
        *,
        fund: FundModel,
        priority: int,
        status: str,
        watch_reason: str,
        risk_level: str,
        target_position: str,
        tags: str,
        note: str,
    ) -> FundWatchlistItemModel:
        item = FundWatchlistItemModel(
            fund=fund,
            priority=priority,
            status=status,
            watch_reason=watch_reason,
            risk_level=risk_level,
            target_position=target_position,
            tags=tags,
            note=note,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_watchlist_item(self, item_id: int) -> FundWatchlistItemModel | None:
        return self.db.scalar(
            select(FundWatchlistItemModel)
            .options(selectinload(FundWatchlistItemModel.fund))
            .where(FundWatchlistItemModel.id == item_id)
        )

    def get_watchlist_item_by_fund_id(self, fund_id: int) -> FundWatchlistItemModel | None:
        return self.db.scalar(
            select(FundWatchlistItemModel)
            .options(selectinload(FundWatchlistItemModel.fund))
            .where(FundWatchlistItemModel.fund_id == fund_id)
        )

    def update_watchlist_item(
        self,
        item: FundWatchlistItemModel,
        *,
        fund: FundModel,
        priority: int,
        status: str,
        watch_reason: str,
        risk_level: str,
        target_position: str,
        tags: str,
        note: str,
    ) -> FundWatchlistItemModel:
        item.fund = fund
        item.priority = priority
        item.status = status
        item.watch_reason = watch_reason
        item.risk_level = risk_level
        item.target_position = target_position
        item.tags = tags
        item.note = note
        item.updated_at = utcnow()
        self.db.flush()
        return item

    def delete_watchlist_item(self, item: FundWatchlistItemModel) -> None:
        self.db.delete(item)
        self.db.flush()

    def upsert_nav_record(
        self,
        *,
        fund: FundModel,
        nav_date: date,
        unit_nav: Decimal,
        accumulated_nav: Decimal | None,
        source: str,
        note: str,
    ) -> FundNavRecordModel:
        record = self.db.scalar(
            select(FundNavRecordModel)
            .options(selectinload(FundNavRecordModel.fund))
            .where(
                FundNavRecordModel.fund_id == fund.id,
                FundNavRecordModel.nav_date == nav_date,
            )
        )
        now = utcnow()
        if record is not None:
            record.unit_nav = unit_nav
            record.accumulated_nav = accumulated_nav
            record.source = source
            record.note = note
            record.updated_at = now
            self.db.flush()
            return record

        record = FundNavRecordModel(
            fund=fund,
            nav_date=nav_date,
            unit_nav=unit_nav,
            accumulated_nav=accumulated_nav,
            source=source,
            note=note,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def upsert_nav_records(
        self,
        *,
        fund: FundModel,
        records: list[tuple[date, Decimal, Decimal | None, str, str]],
    ) -> list[FundNavRecordModel]:
        dates = [record[0] for record in records]
        existing_records = self.db.scalars(
            select(FundNavRecordModel).where(
                FundNavRecordModel.fund_id == fund.id,
                FundNavRecordModel.nav_date.in_(dates),
            )
        )
        existing_by_date = {record.nav_date: record for record in existing_records}
        now = utcnow()
        saved: list[FundNavRecordModel] = []
        for nav_date, unit_nav, accumulated_nav, source, note in records:
            record = existing_by_date.get(nav_date)
            if record is None:
                record = FundNavRecordModel(
                    fund=fund,
                    nav_date=nav_date,
                    unit_nav=unit_nav,
                    accumulated_nav=accumulated_nav,
                    source=source,
                    note=note,
                )
                self.db.add(record)
            else:
                record.unit_nav = unit_nav
                record.accumulated_nav = accumulated_nav
                record.source = source
                record.note = note
                record.updated_at = now
            saved.append(record)
        self.db.flush()
        return saved

    def get_nav_record(self, record_id: int) -> FundNavRecordModel | None:
        return self.db.scalar(
            select(FundNavRecordModel)
            .options(selectinload(FundNavRecordModel.fund))
            .where(FundNavRecordModel.id == record_id)
        )

    def delete_nav_record(self, record: FundNavRecordModel) -> None:
        self.db.delete(record)
        self.db.flush()

    def update_position_navs(self, *, fund_id: int, current_nav: Decimal) -> None:
        positions = self.db.scalars(
            select(FundPositionModel).where(FundPositionModel.fund_id == fund_id)
        )
        now = utcnow()
        for position in positions:
            position.current_nav = current_nav
            position.updated_at = now
        self.db.flush()

    def list_nav_records(self, limit: int = 50) -> list[FundNavRecordModel]:
        return list(
            self.db.scalars(
                select(FundNavRecordModel)
                .options(selectinload(FundNavRecordModel.fund))
                .order_by(FundNavRecordModel.nav_date.desc(), FundNavRecordModel.id.desc())
                .limit(limit)
            )
        )

    def list_latest_nav_records_for_fund_ids(
        self,
        fund_ids: list[int],
    ) -> list[FundNavRecordModel]:
        if not fund_ids:
            return []

        latest_dates = (
            select(
                FundNavRecordModel.fund_id.label("fund_id"),
                func.max(FundNavRecordModel.nav_date).label("latest_nav_date"),
            )
            .where(FundNavRecordModel.fund_id.in_(fund_ids))
            .group_by(FundNavRecordModel.fund_id)
            .subquery()
        )
        return list(
            self.db.scalars(
                select(FundNavRecordModel)
                .join(
                    latest_dates,
                    and_(
                        FundNavRecordModel.fund_id == latest_dates.c.fund_id,
                        FundNavRecordModel.nav_date
                        == latest_dates.c.latest_nav_date,
                    ),
                )
                .options(selectinload(FundNavRecordModel.fund))
                .order_by(FundNavRecordModel.fund_id)
            )
        )

    def list_nav_history(
        self,
        *,
        fund_code: str,
        limit: int,
    ) -> list[FundNavRecordModel]:
        records = list(
            self.db.scalars(
                select(FundNavRecordModel)
                .join(FundModel)
                .options(selectinload(FundNavRecordModel.fund))
                .where(FundModel.code == fund_code)
                .order_by(FundNavRecordModel.nav_date.desc())
                .limit(limit)
            )
        )
        return list(reversed(records))

    def upsert_disclosure(
        self,
        *,
        fund: FundModel,
        report_date: date,
        report_period: str,
        asset_type: str,
        source: str,
        source_url: str,
        holdings: list[
            tuple[
                int,
                str,
                str,
                str,
                Decimal,
                Decimal | None,
                Decimal | None,
            ]
        ],
    ) -> FundDisclosureModel:
        disclosure = self.db.scalar(
            select(FundDisclosureModel)
            .options(selectinload(FundDisclosureModel.holdings))
            .where(
                FundDisclosureModel.fund_id == fund.id,
                FundDisclosureModel.report_date == report_date,
                FundDisclosureModel.asset_type == asset_type,
            )
        )
        now = utcnow()
        if disclosure is None:
            disclosure = FundDisclosureModel(
                fund=fund,
                report_date=report_date,
                report_period=report_period,
                asset_type=asset_type,
                source=source,
                source_url=source_url,
            )
            self.db.add(disclosure)
            self.db.flush()
        else:
            disclosure.report_period = report_period
            disclosure.source = source
            disclosure.source_url = source_url
            disclosure.updated_at = now
            disclosure.holdings.clear()
            self.db.flush()

        disclosure.holdings.extend(
            FundDisclosureHoldingModel(
                rank=rank,
                asset_type=holding_asset_type,
                asset_code=asset_code,
                asset_name=asset_name,
                nav_ratio=nav_ratio,
                reported_quantity=reported_quantity,
                reported_market_value=reported_market_value,
            )
            for (
                rank,
                holding_asset_type,
                asset_code,
                asset_name,
                nav_ratio,
                reported_quantity,
                reported_market_value,
            ) in holdings
        )
        self.db.flush()
        return disclosure

    def list_latest_disclosures(
        self,
        *,
        fund_ids: list[int],
        asset_type: str = "stock",
    ) -> list[FundDisclosureModel]:
        if not fund_ids:
            return []
        records = list(
            self.db.scalars(
                select(FundDisclosureModel)
                .options(
                    selectinload(FundDisclosureModel.fund),
                    selectinload(FundDisclosureModel.holdings),
                )
                .where(
                    FundDisclosureModel.fund_id.in_(fund_ids),
                    FundDisclosureModel.asset_type == asset_type,
                )
                .order_by(
                    FundDisclosureModel.report_date.desc(),
                    FundDisclosureModel.id.desc(),
                )
            )
        )
        latest_by_fund: dict[int, FundDisclosureModel] = {}
        for record in records:
            latest_by_fund.setdefault(record.fund_id, record)
        return list(latest_by_fund.values())

    def get_nav_summary_data(
        self,
    ) -> tuple[int, int, date | None, list[str]]:
        record_count, fund_count, latest_nav_date = self.db.execute(
            select(
                func.count(FundNavRecordModel.id),
                func.count(distinct(FundNavRecordModel.fund_id)),
                func.max(FundNavRecordModel.nav_date),
            )
        ).one()
        sources = list(
            self.db.scalars(
                select(FundNavRecordModel.source)
                .distinct()
                .order_by(FundNavRecordModel.source)
            )
        )
        return record_count, fund_count, latest_nav_date, sources

    def list_watchlist_items(self) -> list[FundWatchlistItemModel]:
        return list(
            self.db.scalars(
                select(FundWatchlistItemModel)
                .options(selectinload(FundWatchlistItemModel.fund))
                .order_by(
                    FundWatchlistItemModel.priority.asc(),
                    FundWatchlistItemModel.created_at.desc(),
                    FundWatchlistItemModel.id.desc(),
                )
            )
        )

    def list_positions(self) -> list[FundPositionModel]:
        return list(
            self.db.scalars(
                select(FundPositionModel)
                .options(selectinload(FundPositionModel.fund))
                .order_by(FundPositionModel.created_at.desc(), FundPositionModel.id.desc())
            )
        )
