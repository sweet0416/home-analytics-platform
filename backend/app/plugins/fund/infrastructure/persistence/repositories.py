from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, selectinload

from app.plugins.fund.infrastructure.persistence.models import (
    FundDisclosureHoldingModel,
    FundDisclosureModel,
    FundModel,
    FundNavRecordModel,
    FundNavSyncRunModel,
    FundPositionModel,
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

    def get_fund_by_code(self, code: str) -> FundModel | None:
        return self.db.scalar(select(FundModel).where(FundModel.code == code))

    def upsert_fund(self, *, code: str, name: str, fund_type: str) -> FundModel:
        fund = self.get_fund_by_code(code)
        now = datetime.utcnow()
        if fund is not None:
            fund.name = name
            fund.fund_type = fund_type
            fund.updated_at = now
            self.db.flush()
            return fund

        fund = FundModel(code=code, name=name, fund_type=fund_type)
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
        position.opened_at = opened_at
        position.tags = tags
        position.note = note
        position.updated_at = datetime.utcnow()
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
        item.updated_at = datetime.utcnow()
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
        now = datetime.utcnow()
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
        now = datetime.utcnow()
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
        now = datetime.utcnow()
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
        now = datetime.utcnow()
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
