from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.infrastructure.persistence.models import (
    LotteryDrawModel,
    LotteryGameModel,
    LotteryPrizeTierModel,
    LotteryRuleVersionModel,
)


class LotteryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_game(self, code: str) -> LotteryGameModel | None:
        return self.db.scalar(select(LotteryGameModel).where(LotteryGameModel.code == code))

    def get_current_rule(self, game_code: str = DLT_GAME_CODE) -> LotteryRuleVersionModel | None:
        statement = (
            select(LotteryRuleVersionModel)
            .options(selectinload(LotteryRuleVersionModel.prize_tiers))
            .where(LotteryRuleVersionModel.game_code == game_code)
            .order_by(LotteryRuleVersionModel.effective_from.desc().nullslast())
        )
        return self.db.scalar(statement)

    def get_rule_by_code(self, rule_code: str) -> LotteryRuleVersionModel | None:
        statement = (
            select(LotteryRuleVersionModel)
            .options(selectinload(LotteryRuleVersionModel.prize_tiers))
            .where(LotteryRuleVersionModel.rule_code == rule_code)
        )
        return self.db.scalar(statement)

    def list_draws(
        self,
        game_code: str = DLT_GAME_CODE,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LotteryDrawModel], int]:
        base_statement: Select[tuple[LotteryDrawModel]] = select(LotteryDrawModel).where(
            LotteryDrawModel.game_code == game_code
        )
        total = self.db.scalar(
            select(func.count()).select_from(base_statement.subquery())
        ) or 0
        items = list(
            self.db.scalars(
                base_statement.order_by(LotteryDrawModel.draw_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def get_latest_draw(self, game_code: str = DLT_GAME_CODE) -> LotteryDrawModel | None:
        return self.db.scalar(
            select(LotteryDrawModel)
            .where(LotteryDrawModel.game_code == game_code)
            .order_by(LotteryDrawModel.draw_date.desc())
            .limit(1)
        )

    def get_draw_by_issue(
        self,
        issue_no: str,
        game_code: str = DLT_GAME_CODE,
    ) -> LotteryDrawModel | None:
        return self.db.scalar(
            select(LotteryDrawModel).where(
                LotteryDrawModel.game_code == game_code,
                LotteryDrawModel.issue_no == issue_no,
            )
        )

    def ensure_dlt_seed_data(self) -> None:
        if self.get_game(DLT_GAME_CODE) is None:
            self.db.add(
                LotteryGameModel(
                    code=DLT_GAME_CODE,
                    name="超级大乐透",
                    region="CN",
                    official_source="sporttery",
                )
            )

        if self.get_rule_by_code("dlt-current-official") is None:
            rule = LotteryRuleVersionModel(
                game_code=DLT_GAME_CODE,
                rule_code="dlt-current-official",
                rule_name="超级大乐透当前官方有效规则",
                effective_from=None,
                effective_to=None,
                front_count=5,
                front_min=1,
                front_max=35,
                back_count=2,
                back_min=1,
                back_max=12,
                base_price=2,
                addon_price=1,
                addon_supported=True,
                official_url="https://www.sporttery.cn/bzzx/20210207/3002858.html?gid=5",
                description="根据当前可查竞彩网官方规则页录入；规则数据版本化保存。",
            )
            rule.prize_tiers = _build_current_dlt_prize_tiers()
            self.db.add(rule)

        self.db.commit()


def _build_current_dlt_prize_tiers() -> list[LotteryPrizeTierModel]:
    rows = [
        (1, "一等奖", 5, 2, True, None, "命中全部前区和后区号码"),
        (2, "二等奖", 5, 1, True, None, "命中5个前区和任意1个后区号码"),
        (3, "三等奖", 5, 0, False, 5000, "命中5个前区号码"),
        (3, "三等奖", 4, 2, False, 5000, "命中任意4个前区和2个后区号码"),
        (4, "四等奖", 4, 1, False, 300, "命中任意4个前区和任意1个后区号码"),
        (5, "五等奖", 4, 0, False, 150, "命中任意4个前区号码"),
        (5, "五等奖", 3, 2, False, 150, "命中任意3个前区和2个后区号码"),
        (6, "六等奖", 3, 1, False, 15, "命中任意3个前区和任意1个后区号码"),
        (6, "六等奖", 2, 2, False, 15, "命中任意2个前区和2个后区号码"),
        (7, "七等奖", 3, 0, False, 5, "命中任意3个前区号码"),
        (7, "七等奖", 2, 1, False, 5, "命中任意2个前区和任意1个后区号码"),
        (7, "七等奖", 1, 2, False, 5, "命中任意1个前区和2个后区号码"),
        (7, "七等奖", 0, 2, False, 5, "命中2个后区号码"),
    ]
    return [
        LotteryPrizeTierModel(
            tier=tier,
            tier_name=tier_name,
            front_match_count=front,
            back_match_count=back,
            is_floating=is_floating,
            base_prize_amount=base_prize,
            addon_multiplier=0.8 if is_floating else None,
            description=description,
            sort_order=index,
        )
        for index, (tier, tier_name, front, back, is_floating, base_prize, description) in enumerate(
            rows,
            start=1,
        )
    ]

