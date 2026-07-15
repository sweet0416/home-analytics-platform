from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.plugins.lottery.application.services import LotteryService
from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawRecord
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository


def test_lottery_service_serializes_current_rule(db_session: Session) -> None:
    LotteryRepository(db_session).ensure_dlt_seed_data()

    rule = LotteryService(db_session).get_current_rule()

    assert rule["rule_code"] == "dlt-current-official"
    assert rule["front"]["max"] == 35
    assert rule["back"]["max"] == 12
    assert len(rule["prize_tiers"]) == 13


def test_lottery_service_returns_basic_statistics(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    repository.upsert_draw(
        DrawRecord(
            game_code=DLT_GAME_CODE,
            issue_no="25001",
            draw_date=date(2026, 1, 1),
            front_numbers=[1, 2, 3, 4, 5],
            back_numbers=[1, 2],
            sales_amount=Decimal("100.00"),
            pool_amount=Decimal("200.00"),
            source_url="https://example.test/1",
            raw_data={"fixture": 1},
        )
    )
    repository.upsert_draw(
        DrawRecord(
            game_code=DLT_GAME_CODE,
            issue_no="25002",
            draw_date=date(2026, 1, 3),
            front_numbers=[1, 6, 7, 8, 9],
            back_numbers=[2, 3],
            sales_amount=Decimal("100.00"),
            pool_amount=Decimal("200.00"),
            source_url="https://example.test/2",
            raw_data={"fixture": 2},
        )
    )
    db_session.commit()

    statistics = LotteryService(db_session).get_basic_statistics(limit=100)

    assert statistics["sample_size"] == 2
    assert statistics["latest_issue_no"] == "25002"
    assert statistics["sum"] == {"min": 15, "max": 31, "average": 23}
    assert statistics["span"] == {"min": 4, "max": 8, "average": 6}
    assert statistics["trend"][0]["issue_no"] == "25001"
    assert statistics["trend"][1]["issue_no"] == "25002"
    assert statistics["recent_metrics"][0]["front_zone_pattern"] == "5:0:0"
    assert statistics["recent_metrics"][0]["front_route012_pattern"] == "2:2:1"
    front_one = next(item for item in statistics["front_frequency"] if item["number"] == 1)
    front_five = next(item for item in statistics["front_frequency"] if item["number"] == 5)
    assert front_one["count"] == 2
    assert front_one["missing"] == 0
    assert front_five["count"] == 1
    assert front_five["missing"] == 1


def test_lottery_service_returns_omission_statistics(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    for index, front_numbers in enumerate(
        (
            [1, 2, 3, 4, 5],
            [2, 6, 7, 8, 9],
            [1, 10, 11, 12, 13],
        ),
        start=1,
    ):
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=f"2500{index}",
                draw_date=date(2026, 1, index),
                front_numbers=front_numbers,
                back_numbers=[1, 2] if index < 3 else [2, 3],
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url=f"https://example.test/{index}",
                raw_data={"fixture": index},
            )
        )
    db_session.commit()

    service = LotteryService(db_session)
    omissions = service.get_omission_statistics(limit=100)
    front_one = next(item for item in omissions["front"] if item["number"] == 1)
    front_five = next(item for item in omissions["front"] if item["number"] == 5)
    back_one = next(item for item in omissions["back"] if item["number"] == 1)

    assert omissions["sample_size"] == 3
    assert omissions["latest_issue_no"] == "25003"
    assert front_one["appearances"] == 2
    assert front_one["current_missing"] == 0
    assert front_one["max_missing"] == 1
    assert front_five["appearances"] == 1
    assert front_five["current_missing"] == 2
    assert back_one["current_missing"] == 1

    detail = service.get_number_omission_detail(area="front", number=1, limit=100)

    assert detail["sample_size"] == 3
    assert [item["issue_no"] for item in detail["hit_issues"]] == ["25003", "25001"]
    assert [item["missing"] for item in detail["trend"]] == [0, 1, 0]
