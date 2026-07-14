from sqlalchemy.orm import Session

from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository


def test_lottery_service_serializes_current_rule(db_session: Session) -> None:
    LotteryRepository(db_session).ensure_dlt_seed_data()

    rule = LotteryService(db_session).get_current_rule()

    assert rule["rule_code"] == "dlt-current-official"
    assert rule["front"]["max"] == 35
    assert rule["back"]["max"] == 12
    assert len(rule["prize_tiers"]) == 13
