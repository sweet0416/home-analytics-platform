from app.core.database.session import SessionLocal, create_database_schema
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository


def test_seed_current_dlt_rule_is_idempotent() -> None:
    create_database_schema()
    db = SessionLocal()
    try:
        repository = LotteryRepository(db)
        repository.ensure_dlt_seed_data()
        repository.ensure_dlt_seed_data()

        rule = repository.get_current_rule()

        assert rule is not None
        assert rule.game_code == "dlt"
        assert rule.rule_name == "超级大乐透当前官方有效规则"
        assert rule.front_count == 5
        assert rule.front_min == 1
        assert rule.front_max == 35
        assert rule.back_count == 2
        assert rule.back_min == 1
        assert rule.back_max == 12
        assert len(rule.prize_tiers) == 13
        assert rule.prize_tiers[0].tier_name == "一等奖"
    finally:
        db.close()
