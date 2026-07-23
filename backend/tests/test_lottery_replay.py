from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.plugins.lottery.application.replay_service import LotteryReplayService
from app.plugins.lottery.domain.constants import DLT_GAME_CODE
from app.plugins.lottery.domain.sync import DrawRecord
from app.plugins.lottery.infrastructure.persistence.models import (
    LotteryReplayGeneratedSetModel,
    LotteryReplayRunModel,
)
from app.plugins.lottery.infrastructure.persistence.repositories import LotteryRepository


def seed_replay_draws(db_session: Session) -> None:
    repository = LotteryRepository(db_session)
    repository.ensure_dlt_seed_data()
    fixtures = [
        ("25076", date(2025, 6, 30), [1, 5, 9, 18, 28], [1, 8]),
        ("25077", date(2025, 7, 2), [2, 6, 10, 19, 29], [2, 9]),
        ("25078", date(2025, 7, 5), [3, 7, 11, 20, 30], [3, 10]),
        ("25079", date(2025, 7, 7), [4, 8, 12, 21, 31], [4, 11]),
        ("24080", date(2024, 7, 8), [1, 9, 14, 23, 33], [1, 12]),
        ("25080", date(2025, 7, 9), [5, 9, 13, 22, 32], [5, 12]),
        ("26080", date(2026, 7, 9), [1, 5, 9, 22, 35], [1, 12]),
        ("26081", date(2026, 7, 12), [6, 16, 20, 25, 34], [2, 10]),
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


def test_replay_context_uses_only_past_draws(db_session: Session) -> None:
    seed_replay_draws(db_session)

    context = LotteryReplayService(db_session).get_replay_context(
        target_issue_no="26080",
        sample_limit=20,
    )

    assert context["target"]["issue_no"] == "26080"
    assert context["cutoff"]["issue_no"] == "25080"
    assert context["sample_size"] == 6
    assert context["available_range"]["latest_issue_no"] == "25080"
    assert context["leakage_check"]["passed"] is True
    assert context["same_period_deviation"]["issue_suffix"] == "080"
    assert context["same_period_deviation"]["sample_size"] == 2


def test_replay_records_generated_sets_and_baseline(db_session: Session) -> None:
    seed_replay_draws(db_session)

    result = LotteryReplayService(db_session).run_replay(
        target_issue_no="26080",
        sets=2,
        sample_limit=20,
        baseline_simulations=500,
        seed=42,
    )

    assert result["run_id"] > 0
    assert result["cutoff_issue_no"] == "25080"
    assert result["sample_size"] == 6
    assert len(result["generated_sets"]) == 2
    assert result["baseline"]["seed"] == 42
    assert result["baseline"]["simulations"] == 500
    assert result["leakage_check"]["passed"] is True
    assert result["same_period_deviation"]["front_repeat"]["level"] in {
        "low",
        "medium",
        "high",
        "sample_limited",
    }

    run_count = db_session.scalar(select(func.count()).select_from(LotteryReplayRunModel))
    set_count = db_session.scalar(select(func.count()).select_from(LotteryReplayGeneratedSetModel))
    assert run_count == 1
    assert set_count == 2


def test_replay_random_baseline_is_seed_reproducible(db_session: Session) -> None:
    seed_replay_draws(db_session)
    service = LotteryReplayService(db_session)

    first = service.run_replay(
        target_issue_no="26080",
        sets=1,
        sample_limit=20,
        baseline_simulations=500,
        seed=7,
    )
    second = service.run_replay(
        target_issue_no="26080",
        sets=1,
        sample_limit=20,
        baseline_simulations=500,
        seed=7,
    )

    assert first["baseline"] == second["baseline"]


def test_replay_endpoint_returns_context_and_run(client: TestClient, db_session: Session) -> None:
    seed_replay_draws(db_session)

    context_response = client.get(
        "/api/v1/lottery/dlt/analysis/replay/context",
        params={"target_issue_no": "26080", "sample_limit": 20},
    )
    run_response = client.post(
        "/api/v1/lottery/dlt/analysis/replay",
        json={
            "target_issue_no": "26080",
            "sets": 2,
            "sample_limit": 20,
            "baseline_simulations": 500,
            "seed": 42,
        },
    )

    assert context_response.status_code == 200
    assert context_response.json()["data"]["cutoff"]["issue_no"] == "25080"
    assert "same_period_deviation" in context_response.json()["data"]
    assert run_response.status_code == 200
    assert run_response.json()["data"]["cutoff_issue_no"] == "25080"
    assert "same_period_deviation" in run_response.json()["data"]
    assert len(run_response.json()["data"]["generated_sets"]) == 2


def test_sensitivity_analysis_does_not_create_replay_run(db_session: Session) -> None:
    seed_replay_draws(db_session)

    result = LotteryReplayService(db_session).analyze_parameter_sensitivity(
        target_issue_no="26080",
        sets=2,
        sample_windows=[20, 50],
        baseline_simulations=500,
        seed=42,
    )

    assert result["target_issue_no"] == "26080"
    assert result["combination_count"] == 8
    assert result["summary"]["stability_label"] in {
        "相对稳定",
        "疑似过拟合",
        "波动较大",
        "样本不足",
    }
    assert result["leakage_check"]["passed"] is True

    run_count = db_session.scalar(select(func.count()).select_from(LotteryReplayRunModel))
    assert run_count == 0


def test_sensitivity_endpoint_returns_ranked_results(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_replay_draws(db_session)

    response = client.post(
        "/api/v1/lottery/dlt/analysis/replay/sensitivity",
        json={
            "target_issue_no": "26080",
            "sets": 2,
            "sample_windows": [20, 50],
            "baseline_simulations": 500,
            "seed": 42,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["combination_count"] == 8
    assert data["results"][0]["profile_name"]
    assert data["baseline"]["simulations"] == 500
