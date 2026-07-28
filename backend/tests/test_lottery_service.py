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


def test_lottery_service_returns_decay_analysis(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("25001", date(2026, 1, 1), [1, 2, 3, 4, 5], [1, 2]),
        ("25002", date(2026, 1, 3), [6, 7, 8, 9, 10], [3, 4]),
        ("25003", date(2026, 1, 5), [6, 11, 12, 13, 14], [3, 5]),
    ]
    for issue_no, draw_date, front_numbers, back_numbers in fixtures:
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=issue_no,
                draw_date=draw_date,
                front_numbers=front_numbers,
                back_numbers=back_numbers,
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url=f"https://example.test/{issue_no}",
                raw_data={"fixture": issue_no},
            )
        )
    db_session.commit()

    analysis = LotteryService(db_session).get_decay_analysis(limit=50, half_life=1, top=5)

    assert analysis["sample_size"] == 3
    assert analysis["latest_issue_no"] == "25003"
    assert analysis["weight_formula"] == "weight = 0.5 ** (distance / half_life)"
    assert analysis["front"]["numbers"][0]["number"] == 6
    assert analysis["front"]["numbers"][0]["raw_count"] == 2
    assert analysis["front"]["numbers"][0]["weighted_rank"] == 1
    assert analysis["front"]["rising_numbers"][0]["rank_delta"] > 0
    assert analysis["back"]["numbers"][0]["number"] == 3


def test_lottery_service_reports_data_stage_quality(db_session: Session) -> None:
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
            pool_amount=None,
            source_url="https://datachart.500.com/dlt/history/history.shtml",
            raw_data={"fixture": 1},
        )
    )
    db_session.commit()

    report = LotteryService(db_session).get_data_stage_report()

    assert report["sample_size"] == 1
    assert report["stages"][0]["stage_code"] == "dlt-current-official"
    assert report["stages"][0]["earliest_issue_no"] == "25001"
    assert report["source_summary"][0]["source"] == "datachart.500.com"
    assert report["quality"]["sales_present_rate"] == 1
    assert report["quality"]["pool_present_rate"] == 0
    assert report["quality"]["rule_bound_rate"] == 0
    assert any("rule_version_id" in warning for warning in report["warnings"])


def test_lottery_service_repairs_data_stage_rule_bindings(db_session: Session) -> None:
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
            source_url="https://datachart.500.com/dlt/history/history.shtml",
            raw_data={"fixture": 1},
        )
    )
    db_session.commit()

    result = LotteryService(db_session).repair_data_stage_bindings()
    draw = repository.get_draw_by_issue("25001")
    rule = repository.get_rule_for_issue_no("25001")

    assert result["repaired_count"] == 1
    assert result["rule_code"] == "staged-rule-binding"
    assert result["stage_report"]["quality"]["rule_bound_rate"] == 1
    assert result["stage_report"]["stages"][0]["stage_code"] == "dlt-2019-official"
    assert draw is not None
    assert rule is not None
    assert draw.rule_version_id == rule.id


def test_lottery_service_binds_rule_stage_boundaries(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("19018", date(2019, 2, 17), "dlt-before-2019-official"),
        ("19019", date(2019, 2, 18), "dlt-2019-official"),
        ("26013", date(2026, 1, 30), "dlt-2019-official"),
        ("26014", date(2026, 1, 31), "dlt-2026-official"),
    ]
    for issue_no, draw_date, _rule_code in fixtures:
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=issue_no,
                draw_date=draw_date,
                front_numbers=[1, 2, 3, 4, 5],
                back_numbers=[1, 2],
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url="https://datachart.500.com/dlt/history/history.shtml",
                raw_data={"fixture": issue_no},
            )
        )
    db_session.commit()

    result = LotteryService(db_session).repair_data_stage_bindings()

    assert result["repaired_count"] == 4
    for issue_no, _draw_date, rule_code in fixtures:
        draw = repository.get_draw_by_issue(issue_no)
        rule = repository.get_rule_by_code(rule_code)
        assert draw is not None
        assert rule is not None
        assert draw.rule_version_id == rule.id


def test_lottery_service_parses_compact_random_ticket_ocr_text() -> None:
    raw_text = """2
2608431 1 202
728

2 2

06414417423433 01406
05426429430432 08411

0306110411435 06410

0412119423427 07409
4

 10 4900
496 284192088 000"""

    rows = LotteryService._parse_random_ticket_ocr_text(raw_text)

    assert rows[:3] == [
        {"rank": 1, "front_numbers": [6, 14, 17, 23, 33], "back_numbers": [1, 6]},
        {"rank": 2, "front_numbers": [5, 26, 29, 30, 32], "back_numbers": [8, 11]},
        {"rank": 3, "front_numbers": [3, 6, 10, 11, 35], "back_numbers": [6, 10]},
    ]


def test_lottery_service_strips_row_index_from_compact_ocr_line() -> None:
    row = LotteryService._parse_compact_random_ticket_line("5 45418420431432 07411")

    assert row == {
        "rank": 0,
        "front_numbers": [15, 18, 20, 31, 32],
        "back_numbers": [7, 11],
        "source_rank": 5,
    }


def test_lottery_service_can_preserve_ocr_source_rank_between_variants() -> None:
    raw_text = """4 04418419423427 07409
5 45418420431432 07411"""

    rows = LotteryService._parse_random_ticket_ocr_text(
        raw_text,
        preserve_source_rank=True,
    )

    assert rows == [
        {
            "rank": 1,
            "front_numbers": [4, 18, 19, 23, 27],
            "back_numbers": [7, 9],
            "source_rank": 4,
        },
        {
            "rank": 2,
            "front_numbers": [15, 18, 20, 31, 32],
            "back_numbers": [7, 11],
            "source_rank": 5,
        },
    ]


def test_lottery_service_prioritizes_source_ranked_ocr_rows() -> None:
    rows = LotteryService._rank_random_ticket_rows(
        [
            {"rank": 0, "front_numbers": [4, 12, 19, 23, 27], "back_numbers": [7, 9]},
            {
                "rank": 0,
                "front_numbers": [15, 18, 20, 31, 32],
                "back_numbers": [7, 11],
                "source_rank": 5,
            },
            {
                "rank": 0,
                "front_numbers": [4, 18, 19, 23, 27],
                "back_numbers": [7, 9],
                "source_rank": 4,
            },
        ]
    )

    assert rows[:3] == [
        {"rank": 1, "front_numbers": [4, 12, 19, 23, 27], "back_numbers": [7, 9]},
        {"rank": 2, "front_numbers": [4, 18, 19, 23, 27], "back_numbers": [7, 9]},
        {"rank": 3, "front_numbers": [15, 18, 20, 31, 32], "back_numbers": [7, 11]},
    ]


def test_lottery_service_preserves_five_ranked_ticket_slots() -> None:
    rows = LotteryService._rank_random_ticket_rows(
        [
            {"rank": 0, "front_numbers": [6, 14, 17, 23, 33], "back_numbers": [1, 6]},
            {"rank": 0, "front_numbers": [5, 26, 29, 30, 32], "back_numbers": [8, 11]},
            {"rank": 0, "front_numbers": [3, 6, 10, 11, 35], "back_numbers": [6, 10]},
            {"rank": 0, "front_numbers": [4, 12, 19, 23, 27], "back_numbers": [7, 9]},
            {
                "rank": 0,
                "front_numbers": [4, 18, 19, 23, 27],
                "back_numbers": [7, 9],
                "source_rank": 4,
            },
            {
                "rank": 0,
                "front_numbers": [15, 18, 20, 31, 32],
                "back_numbers": [7, 11],
                "source_rank": 5,
            },
        ]
    )

    assert rows[:5] == [
        {"rank": 1, "front_numbers": [6, 14, 17, 23, 33], "back_numbers": [1, 6]},
        {"rank": 2, "front_numbers": [5, 26, 29, 30, 32], "back_numbers": [8, 11]},
        {"rank": 3, "front_numbers": [3, 6, 10, 11, 35], "back_numbers": [6, 10]},
        {"rank": 4, "front_numbers": [4, 18, 19, 23, 27], "back_numbers": [7, 9]},
        {"rank": 5, "front_numbers": [15, 18, 20, 31, 32], "back_numbers": [7, 11]},
    ]


def test_lottery_service_keeps_pending_random_ticket_snapshot() -> None:
    items = LotteryService._build_pending_random_ticket_items(
        [
            {"rank": 1, "front_numbers": [6, 14, 17, 23, 33], "back_numbers": [1, 6]},
            {"rank": 2, "front_numbers": [5, 26, 29, 30, 32], "back_numbers": [8, 11]},
        ]
    )

    assert items == [
        {
            "rank": 1,
            "front_numbers": [6, 14, 17, 23, 33],
            "back_numbers": [1, 6],
            "front_matches": [],
            "back_matches": [],
            "front_match_count": 0,
            "back_match_count": 0,
            "match_key": "待开奖",
            "prize_tier": None,
        },
        {
            "rank": 2,
            "front_numbers": [5, 26, 29, 30, 32],
            "back_numbers": [8, 11],
            "front_matches": [],
            "back_matches": [],
            "front_match_count": 0,
            "back_match_count": 0,
            "match_key": "待开奖",
            "prize_tier": None,
        },
    ]


def test_lottery_randomness_diagnostics_can_filter_by_rule_stage(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("19018", date(2019, 2, 17), "dlt-before-2019-official"),
        ("19019", date(2019, 2, 18), "dlt-2019-official"),
        ("26014", date(2026, 1, 31), "dlt-2026-official"),
    ]
    for issue_no, draw_date, rule_code in fixtures:
        rule = repository.get_rule_by_code(rule_code)
        assert rule is not None
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=issue_no,
                draw_date=draw_date,
                front_numbers=[1, 2, 3, 4, 5],
                back_numbers=[1, 2],
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url="https://datachart.500.com/dlt/history/history.shtml",
                raw_data={"fixture": issue_no},
            ),
            rule_version_id=rule.id,
        )
    db_session.commit()

    result = LotteryService(db_session).get_randomness_diagnostics(
        limit=50,
        stage_code="dlt-2026-official",
    )

    assert result["sample_size"] == 1
    assert result["stage_code"] == "dlt-2026-official"
    assert result["stage_name"] == "超级大乐透 2026 当前规则阶段"
    assert result["earliest_issue_no"] == "26014"
    assert result["latest_issue_no"] == "26014"


def test_lottery_decay_analysis_can_filter_by_rule_stage(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("19019", date(2019, 2, 18), "dlt-2019-official"),
        ("26014", date(2026, 1, 31), "dlt-2026-official"),
    ]
    for issue_no, draw_date, rule_code in fixtures:
        rule = repository.get_rule_by_code(rule_code)
        assert rule is not None
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=issue_no,
                draw_date=draw_date,
                front_numbers=[1, 2, 3, 4, 5],
                back_numbers=[1, 2],
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url="https://datachart.500.com/dlt/history/history.shtml",
                raw_data={"fixture": issue_no},
            ),
            rule_version_id=rule.id,
        )
    db_session.commit()

    result = LotteryService(db_session).get_decay_analysis(
        limit=50,
        half_life=50,
        top=5,
        stage_code="dlt-2026-official",
    )

    assert result["sample_size"] == 1
    assert result["stage_code"] == "dlt-2026-official"
    assert result["stage_name"] == "超级大乐透 2026 当前规则阶段"
    assert result["earliest_issue_no"] == "26014"
    assert result["latest_issue_no"] == "26014"


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


def test_lottery_service_returns_same_period_analysis(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("23078", date(2023, 7, 8), [1, 2, 3, 4, 5], [1, 2]),
        ("24078", date(2024, 7, 8), [1, 6, 7, 8, 9], [2, 3]),
        ("25078", date(2025, 7, 8), [10, 11, 12, 13, 14], [4, 5]),
        ("26078", date(2026, 7, 8), [1, 2, 10, 20, 30], [2, 5]),
    ]
    for issue_no, draw_date, front_numbers, back_numbers in fixtures:
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=issue_no,
                draw_date=draw_date,
                front_numbers=front_numbers,
                back_numbers=back_numbers,
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url=f"https://example.test/{issue_no}",
                raw_data={"fixture": issue_no},
            )
        )
    db_session.commit()

    analysis = LotteryService(db_session).get_same_period_analysis(
        issue_no="26078",
        count=2,
    )

    assert analysis["issue_suffix"] == "078"
    assert analysis["target"]["issue_no"] == "26078"
    assert [item["draw"]["issue_no"] for item in analysis["items"]] == ["25078", "24078"]
    assert analysis["items"][0]["front_matches"] == [10]
    assert analysis["items"][0]["back_matches"] == [5]
    assert analysis["items"][1]["front_matches"] == [1]
    assert analysis["items"][1]["back_matches"] == [2]


def test_lottery_service_accepts_issue_suffix_for_same_period(
    db_session: Session,
) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("23080", date(2023, 7, 10), [1, 2, 3, 4, 5], [1, 2]),
        ("24080", date(2024, 7, 10), [1, 6, 7, 8, 9], [2, 3]),
        ("25080", date(2025, 7, 10), [10, 11, 12, 13, 14], [4, 5]),
    ]
    for issue_no, draw_date, front_numbers, back_numbers in fixtures:
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=issue_no,
                draw_date=draw_date,
                front_numbers=front_numbers,
                back_numbers=back_numbers,
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url=f"https://example.test/{issue_no}",
                raw_data={"fixture": issue_no},
            )
        )
    db_session.commit()

    analysis = LotteryService(db_session).get_same_period_analysis(
        issue_no="080",
        count=2,
    )

    assert analysis["issue_suffix"] == "080"
    assert analysis["target"]["issue_no"] == "25080"
    assert [item["draw"]["issue_no"] for item in analysis["items"]] == ["24080", "23080"]


def test_lottery_service_applies_recommendation_weights(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("26076", date(2026, 6, 30), [1, 5, 9, 18, 28], [1, 8]),
        ("26077", date(2026, 7, 2), [2, 6, 10, 19, 29], [2, 9]),
        ("26078", date(2026, 7, 5), [3, 7, 11, 20, 30], [3, 10]),
        ("26079", date(2026, 7, 7), [4, 8, 12, 21, 31], [4, 11]),
        ("25080", date(2025, 7, 9), [5, 9, 13, 22, 32], [5, 12]),
        ("24080", date(2024, 7, 8), [1, 9, 14, 23, 33], [1, 12]),
    ]
    for issue_no, draw_date, front_numbers, back_numbers in fixtures:
        repository.upsert_draw(
            DrawRecord(
                game_code=DLT_GAME_CODE,
                issue_no=issue_no,
                draw_date=draw_date,
                front_numbers=front_numbers,
                back_numbers=back_numbers,
                sales_amount=Decimal("100.00"),
                pool_amount=Decimal("200.00"),
                source_url=f"https://example.test/{issue_no}",
                raw_data={"fixture": issue_no},
            )
        )
    db_session.commit()

    analysis = LotteryService(db_session).get_recommendations(
        issue_no="26080",
        sets=2,
        same_period_count=2,
        sample_limit=50,
        same_period_weight=80,
        frequency_weight=10,
        missing_weight=5,
        structure_weight=20,
        co_occurrence_weight=15,
        coverage_weight=16,
    )

    assert analysis["strategy_weights"] == {
        "same_period": 80,
        "frequency": 10,
        "missing": 5,
        "structure": 20,
        "co_occurrence": 15,
        "coverage": 16,
    }
    assert analysis["requested_sets"] == 2
    assert len(analysis["recommendations"]) == 2
    assert "co_occurrence_score" in analysis["recommendations"][0]["front_details"][0]
    assert any(
        "覆盖分散" in reason for reason in analysis["recommendations"][0]["rationale"]
    )


def test_recommendation_similarity_blocks_repeated_front_set() -> None:
    selected = [
        {
            "front_numbers": [1, 2, 3, 4, 5],
            "back_numbers": [1, 2],
        }
    ]

    assert LotteryService._is_recommendation_too_similar(
        {
            "front_numbers": [1, 2, 3, 4, 5],
            "back_numbers": [3, 4],
        },
        selected,
    )


def test_recommendation_similarity_blocks_three_front_overlap() -> None:
    selected = [
        {
            "front_numbers": [1, 2, 3, 4, 5],
            "back_numbers": [1, 2],
        }
    ]

    assert LotteryService._is_recommendation_too_similar(
        {
            "front_numbers": [1, 2, 3, 8, 9],
            "back_numbers": [3, 4],
        },
        selected,
    )


def test_same_period_weight_is_reduced_for_small_sample() -> None:
    weights = {
        "same_period": 45.0,
        "frequency": 25.0,
        "missing": 20.0,
        "structure": 10.0,
        "co_occurrence": 15.0,
        "coverage": 16.0,
    }

    adjusted = LotteryService._adjust_same_period_weight_for_sample_size(
        strategy_weights=weights,
        sample_size=3,
        requested_size=10,
    )

    assert adjusted["same_period"] == 13.5
    assert adjusted["coverage"] == 21.6
    assert weights["same_period"] == 45.0


def test_recommendation_similarity_blocks_overused_front_anchor() -> None:
    selected = [
        {"front_numbers": [1, 2, 3, 4, 5], "back_numbers": [1, 2]},
        {"front_numbers": [1, 6, 7, 8, 9], "back_numbers": [3, 4]},
        {"front_numbers": [1, 10, 11, 12, 13], "back_numbers": [5, 6]},
    ]

    assert LotteryService._is_recommendation_too_similar(
        {"front_numbers": [1, 14, 15, 16, 17], "back_numbers": [7, 8]},
        selected,
    )


def test_lottery_service_analyzes_combination_coverage(db_session: Session) -> None:
    LotteryRepository(db_session).ensure_dlt_seed_data()

    analysis = LotteryService(db_session).analyze_combination_coverage(
        combinations=[
            {"front_numbers": [1, 2, 3, 4, 5], "back_numbers": [1, 2]},
            {"front_numbers": [1, 6, 7, 8, 9], "back_numbers": [2, 3]},
            {"front_numbers": [10, 11, 12, 13, 14], "back_numbers": [4, 5]},
        ],
    )

    assert analysis["set_count"] == 3
    assert analysis["front_unique_count"] == 14
    assert analysis["back_unique_count"] == 5
    assert analysis["front_duplicate_slots"] == 1
    assert analysis["back_duplicate_slots"] == 1
    assert analysis["pairwise_similarity"][0]["combined_jaccard"] > 0
    assert analysis["front_entropy"]["normalized"] > 0
