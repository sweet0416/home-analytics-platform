from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.plugins.fund.infrastructure.persistence.models import FundModel, FundPositionModel


class FundRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        self.db.commit()

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

    def list_positions(self) -> list[FundPositionModel]:
        return list(
            self.db.scalars(
                select(FundPositionModel)
                .options(selectinload(FundPositionModel.fund))
                .order_by(FundPositionModel.created_at.desc(), FundPositionModel.id.desc())
            )
        )
