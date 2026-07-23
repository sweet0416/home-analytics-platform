import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawRecord
from app.plugins.lottery.infrastructure.persistence.models import (
    LotteryDrawModel,
    LotteryGameModel,
    LotteryPrizeTierModel,
    LotteryReplayGeneratedSetModel,
    LotteryReplayRunModel,
    LotteryRuleVersionModel,
    LotterySavedCombinationModel,
    LotterySyncRunModel,
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
        total = self.db.scalar(select(func.count()).select_from(base_statement.subquery())) or 0
        items = list(
            self.db.scalars(
                base_statement.order_by(LotteryDrawModel.draw_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def count_draws(self, game_code: str = DLT_GAME_CODE) -> int:
        return (
            self.db.scalar(
                select(func.count()).select_from(
                    select(LotteryDrawModel)
                    .where(LotteryDrawModel.game_code == game_code)
                    .subquery()
                )
            )
            or 0
        )

    def get_latest_draw(self, game_code: str = DLT_GAME_CODE) -> LotteryDrawModel | None:
        return self.db.scalar(
            select(LotteryDrawModel)
            .where(LotteryDrawModel.game_code == game_code)
            .order_by(LotteryDrawModel.draw_date.desc())
            .limit(1)
        )

    def get_earliest_draw(self, game_code: str = DLT_GAME_CODE) -> LotteryDrawModel | None:
        return self.db.scalar(
            select(LotteryDrawModel)
            .where(LotteryDrawModel.game_code == game_code)
            .order_by(LotteryDrawModel.draw_date.asc())
            .limit(1)
        )

    def list_recent_draws(
        self,
        *,
        game_code: str = DLT_GAME_CODE,
        limit: int = 100,
    ) -> list[LotteryDrawModel]:
        return list(
            self.db.scalars(
                select(LotteryDrawModel)
                .where(LotteryDrawModel.game_code == game_code)
                .order_by(LotteryDrawModel.draw_date.desc())
                .limit(limit)
            )
        )

    def list_all_draws(self, game_code: str = DLT_GAME_CODE) -> list[LotteryDrawModel]:
        return list(
            self.db.scalars(
                select(LotteryDrawModel)
                .where(LotteryDrawModel.game_code == game_code)
                .order_by(LotteryDrawModel.draw_date.desc())
            )
        )

    def list_draws_before_issue(
        self,
        target_issue_no: str,
        *,
        game_code: str = DLT_GAME_CODE,
        limit: int | None = None,
    ) -> list[LotteryDrawModel]:
        statement = (
            select(LotteryDrawModel)
            .where(
                LotteryDrawModel.game_code == game_code,
                LotteryDrawModel.issue_no < target_issue_no,
            )
            .order_by(LotteryDrawModel.draw_date.desc(), LotteryDrawModel.issue_no.desc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.scalars(statement))

    def get_previous_draw(
        self,
        target_issue_no: str,
        *,
        game_code: str = DLT_GAME_CODE,
    ) -> LotteryDrawModel | None:
        return self.db.scalar(
            select(LotteryDrawModel)
            .where(
                LotteryDrawModel.game_code == game_code,
                LotteryDrawModel.issue_no < target_issue_no,
            )
            .order_by(LotteryDrawModel.issue_no.desc())
            .limit(1)
        )

    def list_saved_combinations(
        self,
        game_code: str = DLT_GAME_CODE,
    ) -> list[LotterySavedCombinationModel]:
        return list(
            self.db.scalars(
                select(LotterySavedCombinationModel)
                .where(LotterySavedCombinationModel.game_code == game_code)
                .order_by(
                    LotterySavedCombinationModel.favorite.desc(),
                    LotterySavedCombinationModel.updated_at.desc(),
                )
            )
        )

    def get_saved_combination(
        self,
        combination_id: int,
        game_code: str = DLT_GAME_CODE,
    ) -> LotterySavedCombinationModel | None:
        return self.db.scalar(
            select(LotterySavedCombinationModel).where(
                LotterySavedCombinationModel.id == combination_id,
                LotterySavedCombinationModel.game_code == game_code,
            )
        )

    def get_saved_combination_by_numbers(
        self,
        *,
        front_numbers_json: str,
        back_numbers_json: str,
        game_code: str = DLT_GAME_CODE,
    ) -> LotterySavedCombinationModel | None:
        return self.db.scalar(
            select(LotterySavedCombinationModel).where(
                LotterySavedCombinationModel.game_code == game_code,
                LotterySavedCombinationModel.front_numbers_json == front_numbers_json,
                LotterySavedCombinationModel.back_numbers_json == back_numbers_json,
            )
        )

    def save_combination(
        self,
        *,
        label: str,
        source: str,
        front_numbers_json: str,
        back_numbers_json: str,
        favorite: bool,
        note: str,
        game_code: str = DLT_GAME_CODE,
    ) -> LotterySavedCombinationModel:
        existing = self.get_saved_combination_by_numbers(
            front_numbers_json=front_numbers_json,
            back_numbers_json=back_numbers_json,
            game_code=game_code,
        )
        now = datetime.utcnow()
        if existing is not None:
            existing.label = label
            existing.source = source
            existing.favorite = favorite
            existing.note = note
            existing.updated_at = now
            self.db.flush()
            return existing

        combination = LotterySavedCombinationModel(
            game_code=game_code,
            label=label,
            source=source,
            front_numbers_json=front_numbers_json,
            back_numbers_json=back_numbers_json,
            favorite=favorite,
            note=note,
        )
        self.db.add(combination)
        self.db.flush()
        return combination

    def update_saved_combination(
        self,
        combination: LotterySavedCombinationModel,
        *,
        label: str | None = None,
        source: str | None = None,
        favorite: bool | None = None,
        note: str | None = None,
    ) -> LotterySavedCombinationModel:
        if label is not None:
            combination.label = label
        if source is not None:
            combination.source = source
        if favorite is not None:
            combination.favorite = favorite
        if note is not None:
            combination.note = note
        combination.updated_at = datetime.utcnow()
        self.db.flush()
        return combination

    def delete_saved_combination(self, combination: LotterySavedCombinationModel) -> None:
        self.db.delete(combination)
        self.db.flush()

    def create_replay_run(
        self,
        *,
        game_code: str,
        target_issue_no: str,
        target_draw_date,
        cutoff_issue_no: str | None,
        cutoff_draw_date,
        strategy_name: str,
        strategy_params_json: str,
        sample_size: int,
        baseline_simulations: int,
        status: str,
        warnings_json: str,
        result_summary_json: str,
    ) -> LotteryReplayRunModel:
        run = LotteryReplayRunModel(
            game_code=game_code,
            target_issue_no=target_issue_no,
            target_draw_date=target_draw_date,
            cutoff_issue_no=cutoff_issue_no,
            cutoff_draw_date=cutoff_draw_date,
            strategy_name=strategy_name,
            strategy_params_json=strategy_params_json,
            sample_size=sample_size,
            baseline_simulations=baseline_simulations,
            status=status,
            warnings_json=warnings_json,
            result_summary_json=result_summary_json,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def add_replay_generated_set(
        self,
        *,
        replay_run: LotteryReplayRunModel,
        rank: int,
        front_numbers_json: str,
        back_numbers_json: str,
        score: Decimal | None,
        rationale_json: str,
        front_match_count: int,
        back_match_count: int,
        prize_tier: int | None,
        baseline_percentile: Decimal | None,
    ) -> LotteryReplayGeneratedSetModel:
        generated_set = LotteryReplayGeneratedSetModel(
            replay_run=replay_run,
            rank=rank,
            front_numbers_json=front_numbers_json,
            back_numbers_json=back_numbers_json,
            score=score,
            rationale_json=rationale_json,
            front_match_count=front_match_count,
            back_match_count=back_match_count,
            prize_tier=prize_tier,
            baseline_percentile=baseline_percentile,
        )
        self.db.add(generated_set)
        self.db.flush()
        return generated_set

    def list_replay_runs(
        self,
        *,
        game_code: str = DLT_GAME_CODE,
        limit: int = 20,
    ) -> list[LotteryReplayRunModel]:
        return list(
            self.db.scalars(
                select(LotteryReplayRunModel)
                .where(LotteryReplayRunModel.game_code == game_code)
                .options(selectinload(LotteryReplayRunModel.generated_sets))
                .order_by(LotteryReplayRunModel.created_at.desc(), LotteryReplayRunModel.id.desc())
                .limit(limit)
            )
        )

    def get_replay_run(
        self,
        replay_run_id: int,
        *,
        game_code: str = DLT_GAME_CODE,
    ) -> LotteryReplayRunModel | None:
        return self.db.scalar(
            select(LotteryReplayRunModel)
            .where(
                LotteryReplayRunModel.id == replay_run_id,
                LotteryReplayRunModel.game_code == game_code,
            )
            .options(selectinload(LotteryReplayRunModel.generated_sets))
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

    def list_draws_by_issue_suffix(
        self,
        *,
        issue_suffix: str,
        exclude_issue_no: str | None = None,
        game_code: str = DLT_GAME_CODE,
        limit: int = 5,
    ) -> list[LotteryDrawModel]:
        statement = select(LotteryDrawModel).where(
            LotteryDrawModel.game_code == game_code,
            LotteryDrawModel.issue_no.like(f"%{issue_suffix}"),
        )
        if exclude_issue_no is not None:
            statement = statement.where(LotteryDrawModel.issue_no != exclude_issue_no)

        return list(
            self.db.scalars(
                statement.order_by(LotteryDrawModel.issue_no.desc()).limit(limit)
            )
        )

    def get_latest_draw_by_issue_suffix(
        self,
        *,
        issue_suffix: str,
        game_code: str = DLT_GAME_CODE,
    ) -> LotteryDrawModel | None:
        return self.db.scalar(
            select(LotteryDrawModel)
            .where(
                LotteryDrawModel.game_code == game_code,
                LotteryDrawModel.issue_no.like(f"%{issue_suffix}"),
            )
            .order_by(LotteryDrawModel.issue_no.desc())
            .limit(1)
        )

    def has_running_sync(self, game_code: str = DLT_GAME_CODE) -> bool:
        running_id = self.db.scalar(
            select(LotterySyncRunModel.id)
            .where(
                LotterySyncRunModel.game_code == game_code,
                LotterySyncRunModel.status == "running",
            )
            .limit(1)
        )
        return running_id is not None

    def create_sync_run(
        self,
        *,
        game_code: str,
        source: str,
        sync_type: str,
        requested_page: int,
        requested_page_size: int,
        source_url: str | None,
    ) -> LotterySyncRunModel:
        run = LotterySyncRunModel(
            game_code=game_code,
            source=source,
            sync_type=sync_type,
            status="running",
            requested_page=requested_page,
            requested_page_size=requested_page_size,
            source_url=source_url,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish_sync_run(
        self,
        run: LotterySyncRunModel,
        *,
        status: str,
        fetched_count: int,
        inserted_count: int,
        updated_count: int,
        skipped_count: int,
        failed_count: int,
        latest_issue_no: str | None,
        error_code: str | None = None,
        error_message: str | None = None,
        raw_metadata: dict[str, object] | None = None,
        source: str | None = None,
        source_url: str | None = None,
    ) -> LotterySyncRunModel:
        finished_at = datetime.utcnow()
        run.status = status
        run.finished_at = finished_at
        run.duration_ms = int((finished_at - run.started_at).total_seconds() * 1000)
        run.fetched_count = fetched_count
        run.inserted_count = inserted_count
        run.updated_count = updated_count
        run.skipped_count = skipped_count
        run.failed_count = failed_count
        run.latest_issue_no = latest_issue_no
        run.error_code = error_code
        run.error_message = error_message
        if source is not None:
            run.source = source
        if source_url is not None:
            run.source_url = source_url
        run.raw_metadata_json = json.dumps(raw_metadata or {}, ensure_ascii=False)
        run.updated_at = finished_at
        self.db.flush()
        return run

    def get_latest_sync_run(self, game_code: str = DLT_GAME_CODE) -> LotterySyncRunModel | None:
        return self.db.scalar(
            select(LotterySyncRunModel)
            .where(LotterySyncRunModel.game_code == game_code)
            .order_by(LotterySyncRunModel.started_at.desc())
            .limit(1)
        )

    def list_sync_runs(
        self,
        *,
        game_code: str = DLT_GAME_CODE,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sync_type: str | None = None,
    ) -> tuple[list[LotterySyncRunModel], int]:
        base_statement: Select[tuple[LotterySyncRunModel]] = select(LotterySyncRunModel).where(
            LotterySyncRunModel.game_code == game_code
        )
        if status is not None:
            base_statement = base_statement.where(LotterySyncRunModel.status == status)
        if sync_type is not None:
            base_statement = base_statement.where(LotterySyncRunModel.sync_type == sync_type)

        total = self.db.scalar(select(func.count()).select_from(base_statement.subquery())) or 0
        items = list(
            self.db.scalars(
                base_statement.order_by(LotterySyncRunModel.started_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def upsert_draw(self, record: DrawRecord, *, force: bool = False) -> str:
        existing = self.get_draw_by_issue(record.issue_no, record.game_code)
        front_numbers_json = json.dumps(record.front_numbers, ensure_ascii=False)
        back_numbers_json = json.dumps(record.back_numbers, ensure_ascii=False)
        raw_data_json = json.dumps(record.raw_data, ensure_ascii=False)

        if existing is None:
            self.db.add(
                LotteryDrawModel(
                    game_code=record.game_code,
                    issue_no=record.issue_no,
                    draw_date=record.draw_date,
                    front_numbers_json=front_numbers_json,
                    back_numbers_json=back_numbers_json,
                    sales_amount=record.sales_amount,
                    pool_amount=record.pool_amount,
                    source_url=record.source_url,
                    raw_data_json=raw_data_json,
                )
            )
            return "inserted"

        changed = (
            existing.draw_date != record.draw_date
            or existing.front_numbers_json != front_numbers_json
            or existing.back_numbers_json != back_numbers_json
            or existing.sales_amount != record.sales_amount
            or existing.pool_amount != record.pool_amount
        )
        if not changed and not force:
            return "skipped"

        existing.draw_date = record.draw_date
        existing.front_numbers_json = front_numbers_json
        existing.back_numbers_json = back_numbers_json
        existing.sales_amount = record.sales_amount
        existing.pool_amount = record.pool_amount
        existing.source_url = record.source_url
        existing.raw_data_json = raw_data_json
        existing.updated_at = datetime.utcnow()
        return "updated"

    def ensure_dlt_seed_data(self) -> None:
        game = self.get_game(DLT_GAME_CODE)
        if game is None:
            self.db.add(
                LotteryGameModel(
                    code=DLT_GAME_CODE,
                    name="超级大乐透",
                    region="CN",
                    official_source="sporttery",
                )
            )
        else:
            game.name = "超级大乐透"
            game.official_source = "sporttery"
            game.updated_at = datetime.utcnow()

        rule = self.get_rule_by_code("dlt-current-official")
        if rule is None:
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
                base_price=Decimal("2.00"),
                addon_price=Decimal("1.00"),
                addon_supported=True,
                official_url="https://www.sporttery.cn/bzzx/20210207/3002858.html?gid=5",
                description="根据中国体育彩票官方规则页录入；规则数据版本化保存。",
            )
            self.db.add(rule)
        else:
            rule.rule_name = "超级大乐透当前官方有效规则"
            rule.description = "根据中国体育彩票官方规则页录入；规则数据版本化保存。"
            rule.official_url = "https://www.sporttery.cn/bzzx/20210207/3002858.html?gid=5"
            rule.updated_at = datetime.utcnow()
            rule.prize_tiers.clear()

        rule.prize_tiers = _build_current_dlt_prize_tiers()
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
            addon_multiplier=Decimal("0.80") if is_floating else None,
            description=description,
            sort_order=index,
        )
        for index, (tier, tier_name, front, back, is_floating, base_prize, description) in enumerate(
            rows,
            start=1,
        )
    ]
