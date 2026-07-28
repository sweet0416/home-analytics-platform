from decimal import Decimal

from app.plugins.fund.infrastructure.persistence.models import (
    FundModel,
    FundPositionModel,
    FundWatchlistItemModel,
)
from app.plugins.fund.infrastructure.persistence.repositories import FundRepository
from app.plugins.fund.interfaces.schemas import (
    FundHoldingSummaryRead,
    FundPositionCreate,
    FundPositionRead,
    FundPositionUpdate,
    FundWatchlistCreate,
    FundWatchlistRead,
    FundWatchlistSummaryRead,
    FundWatchlistUpdate,
)
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class FundService:
    def __init__(self, repository: FundRepository) -> None:
        self.repository = repository

    def list_positions(self) -> list[FundPositionRead]:
        return [self._to_position_read(position) for position in self.repository.list_positions()]

    def list_watchlist_items(self) -> list[FundWatchlistRead]:
        return [self._to_watchlist_read(item) for item in self.repository.list_watchlist_items()]

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
        unrealized_profit = current_value - total_cost if valued_positions else None
        unrealized_return_rate = (
            unrealized_profit / total_cost
            if unrealized_profit is not None and total_cost > 0
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

    def get_watchlist_summary(self) -> FundWatchlistSummaryRead:
        items = self.repository.list_watchlist_items()
        return FundWatchlistSummaryRead(
            item_count=len(items),
            fund_count=len({item.fund_id for item in items}),
            high_priority_count=len([item for item in items if item.priority <= 2]),
            statuses=sorted({item.status for item in items}),
            risk_levels=sorted({item.risk_level for item in items}),
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
