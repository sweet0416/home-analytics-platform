import pytest
from fastapi.testclient import TestClient

from app.plugins.fund.infrastructure.sources.eastmoney import EastmoneyFundNavSource, FundLatestNav


def test_eastmoney_fund_nav_source_parses_latest_record() -> None:
    source = EastmoneyFundNavSource()
    content = """
    var fS_name = "测试基金";
    var fS_code = "513199";
    var Data_netWorthTrend = [
      {"x":1785196800000,"y":1.2000,"equityReturn":0.1},
      {"x":1785283200000,"y":1.3000,"equityReturn":0.2}
    ];
    var Data_ACWorthTrend = [[1785196800000,1.5000],[1785283200000,1.6000]];
    """

    latest = source.parse_script(
        content,
        source_url="https://fund.eastmoney.com/pingzhongdata/513199.js",
        fund_code="513199",
        fund_type="ETF",
    )

    assert latest.fund_code == "513199"
    assert latest.fund_name == "测试基金"
    assert str(latest.unit_nav) == "1.3000"
    assert str(latest.accumulated_nav) == "1.6000"
    assert latest.fund_type == "ETF"


def test_eastmoney_fund_nav_source_parses_history() -> None:
    source = EastmoneyFundNavSource()
    content = """
    var fS_name = "History Fund";
    var fS_code = "513199";
    var Data_netWorthTrend = [
      {"x":1785196800000,"y":1.2000},
      {"x":1785283200000,"y":1.3000},
      {"x":1785369600000,"y":1.2500}
    ];
    var Data_ACWorthTrend = [
      [1785196800000,1.5000],
      [1785283200000,1.6000],
      [1785369600000,1.5500]
    ];
    """

    history = source.parse_history_script(
        content,
        source_url="https://fund.eastmoney.com/pingzhongdata/513199.js",
        fund_code="513199",
        fund_type="ETF",
        limit=2,
    )

    assert len(history) == 2
    assert history[0].nav_date < history[1].nav_date
    assert str(history[0].unit_nav) == "1.3000"
    assert str(history[1].accumulated_nav) == "1.5500"


def test_fund_lookup_latest_nav_does_not_persist(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeNavSource:
        def fetch_latest(
            self,
            fund_code: str,
            fund_type: str = "unknown",
        ) -> FundLatestNav:
            from datetime import date
            from decimal import Decimal

            return FundLatestNav(
                fund_code=fund_code,
                fund_name="测试基金",
                fund_type=fund_type,
                nav_date=date(2026, 7, 28),
                unit_nav=Decimal("1.2300"),
                accumulated_nav=Decimal("1.5600"),
                source="fake",
                source_url="https://example.test/fund.js",
            )

    def build_fake_source(self: object) -> FakeNavSource:
        return FakeNavSource()

    monkeypatch.setattr(
        "app.plugins.fund.application.services.FundService._build_default_nav_source",
        build_fake_source,
    )

    response = client.post(
        "/api/v1/fund/lookup/latest-nav",
        json={"fund_code": "513199", "fund_type": "ETF"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["fund_code"] == "513199"
    assert body["fund_name"] == "测试基金"
    assert body["unit_nav"] == "1.2300"

    nav_records_response = client.get("/api/v1/fund/nav-records")
    assert nav_records_response.status_code == 200
    assert nav_records_response.json()["data"] == []


def test_fund_watchlist_nav_sync_isolates_source_failures(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import date
    from decimal import Decimal

    for fund_code in ("513199", "000404"):
        response = client.post(
            "/api/v1/fund/watchlist",
            json={
                "fund_code": fund_code,
                "fund_name": f"Fund {fund_code}",
                "fund_type": "ETF",
                "priority": 3,
                "status": "watching",
                "watch_reason": "",
                "risk_level": "medium",
                "target_position": "",
                "tags": "",
                "note": "",
            },
        )
        assert response.status_code == 200

    class FakeNavSource:
        def fetch_latest(
            self,
            fund_code: str,
            fund_type: str = "unknown",
        ) -> FundLatestNav:
            if fund_code == "000404":
                raise RuntimeError("source unavailable")
            return FundLatestNav(
                fund_code=fund_code,
                fund_name=f"Fund {fund_code}",
                fund_type=fund_type,
                nav_date=date(2026, 7, 29),
                unit_nav=Decimal("1.2300"),
                accumulated_nav=Decimal("1.5600"),
                source="fake",
                source_url="https://example.test/fund.js",
            )

    monkeypatch.setattr(
        "app.plugins.fund.application.services.FundService._build_default_nav_source",
        lambda self: FakeNavSource(),
    )

    response = client.post("/api/v1/fund/watchlist/sync-nav")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 2
    assert body["succeeded"] == 1
    assert body["failed"] == 1
    assert {item["status"] for item in body["items"]} == {"succeeded", "failed"}

    nav_records = client.get("/api/v1/fund/nav-records").json()["data"]
    assert len(nav_records) == 1
    assert nav_records[0]["fund_code"] == "513199"


def test_fund_nav_history_sync_persists_ordered_series(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import date
    from decimal import Decimal

    class FakeHistorySource:
        def fetch_history(
            self,
            fund_code: str,
            fund_type: str = "unknown",
            limit: int = 365,
        ) -> list[FundLatestNav]:
            return [
                FundLatestNav(
                    fund_code=fund_code,
                    fund_name="History Fund",
                    fund_type=fund_type,
                    nav_date=date(2026, 7, day),
                    unit_nav=Decimal(nav),
                    accumulated_nav=Decimal(nav),
                    source="fake",
                    source_url="https://example.test/history.js",
                )
                for day, nav in ((27, "1.1000"), (28, "1.2000"), (29, "1.3000"))
            ][-limit:]

    monkeypatch.setattr(
        "app.plugins.fund.application.services.FundService._build_default_nav_source",
        lambda self: FakeHistorySource(),
    )

    response = client.post(
        "/api/v1/fund/nav-records/sync-history",
        json={"fund_code": "513199", "fund_type": "ETF", "limit": 3},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["synced_count"] == 3
    assert body["earliest_date"] == "2026-07-27"
    assert body["latest_date"] == "2026-07-29"

    history_response = client.get(
        "/api/v1/fund/nav-records/history",
        params={"fund_code": "513199", "limit": 3},
    )
    assert history_response.status_code == 200
    history = history_response.json()["data"]
    assert [item["nav_date"] for item in history] == [
        "2026-07-27",
        "2026-07-28",
        "2026-07-29",
    ]


def test_health_check_returns_standard_response(client: TestClient) -> None:
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["status"] == "ok"
    assert "x-trace-id" in response.headers


def test_plugins_endpoint_returns_registered_plugins(client: TestClient) -> None:
    response = client.get("/api/v1/plugins")

    assert response.status_code == 200
    plugins = response.json()["data"]
    assert any(plugin["name"] == "lottery" for plugin in plugins)
    assert any(plugin["name"] == "fund" for plugin in plugins)


def test_fund_status_endpoint_returns_scaffold_contract(client: TestClient) -> None:
    response = client.get("/api/v1/fund/status")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["plugin"] == "fund"
    assert body["status"] == "scaffolded"
    assert body["data_source_status"] == "not_configured"
    assert body["storage_status"] == "created"
    assert len(body["modules"]) >= 4


def test_fund_positions_can_be_created_and_summarized(client: TestClient) -> None:
    empty_summary_response = client.get("/api/v1/fund/holdings/summary")
    assert empty_summary_response.status_code == 200
    assert empty_summary_response.json()["data"]["position_count"] == 0

    payload = {
        "fund_code": "513100",
        "fund_name": "纳指 ETF",
        "fund_type": "QDII",
        "account_name": "默认账户",
        "shares": "1000",
        "cost_price": "1.2000",
        "current_nav": "1.3000",
        "opened_at": "2026-07-01",
        "tags": "海外,指数",
        "note": "contract test",
    }
    create_response = client.post("/api/v1/fund/positions", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["fund_code"] == "513100"
    assert created["total_cost"] == "1200.00"
    assert created["current_value"] == "1300.0000"
    assert created["unrealized_profit"] == "100.0000"

    list_response = client.get("/api/v1/fund/positions")
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    summary_response = client.get("/api/v1/fund/holdings/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()["data"]
    assert summary["position_count"] == 1
    assert summary["fund_count"] == 1
    assert summary["total_cost"] == "1200.00"
    assert summary["current_value"] == "1300.0000"

    update_response = client.put(
        f"/api/v1/fund/positions/{created['id']}",
        json={**payload, "current_nav": "1.4000", "note": "updated"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["current_value"] == "1400.0000"
    assert updated["unrealized_profit"] == "200.0000"
    assert updated["note"] == "updated"

    delete_response = client.delete(f"/api/v1/fund/positions/{created['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"] == {"deleted": True, "id": created["id"]}

    final_summary_response = client.get("/api/v1/fund/holdings/summary")
    assert final_summary_response.status_code == 200
    assert final_summary_response.json()["data"]["position_count"] == 0


def test_fund_allocation_uses_nav_and_cost_fallback(client: TestClient) -> None:
    payloads = [
        {
            "fund_code": "510300",
            "fund_name": "Core ETF",
            "fund_type": "ETF",
            "account_name": "Account A",
            "shares": "100",
            "cost_price": "1.0000",
            "current_nav": "2.0000",
            "tags": "",
            "note": "",
        },
        {
            "fund_code": "510300",
            "fund_name": "Core ETF",
            "fund_type": "ETF",
            "account_name": "Account B",
            "shares": "100",
            "cost_price": "1.0000",
            "tags": "",
            "note": "",
        },
        {
            "fund_code": "513100",
            "fund_name": "Overseas Fund",
            "fund_type": "QDII",
            "account_name": "Account B",
            "shares": "100",
            "cost_price": "2.0000",
            "current_nav": "2.0000",
            "tags": "",
            "note": "",
        },
    ]
    for payload in payloads:
        response = client.post("/api/v1/fund/positions", json=payload)
        assert response.status_code == 200

    response = client.get("/api/v1/fund/holdings/allocation")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["position_count"] == 3
    assert body["total_amount"] == "500.0000"
    assert body["current_nav_count"] == 2
    assert body["cost_fallback_count"] == 1
    assert body["top_holding_weight"] == "0.6"
    assert body["concentration_hhi"] == "0.52"
    assert body["by_fund_type"][0]["label"] == "ETF"
    assert body["by_fund_type"][0]["weight"] == "0.6"
    assert {holding["valuation_basis"] for holding in body["holdings"]} == {
        "current_nav",
        "cost",
    }


def test_fund_daily_report_summarizes_data_quality(client: TestClient) -> None:
    empty_response = client.get("/api/v1/fund/reports/daily")
    assert empty_response.status_code == 200
    empty = empty_response.json()["data"]
    assert empty["holding_summary"]["position_count"] == 0
    assert empty["valuation_complete"] is False
    assert {alert["code"] for alert in empty["alerts"]} == {
        "no_positions",
        "nav_missing",
        "watchlist_empty",
    }

    payloads = [
        {
            "fund_code": "510300",
            "fund_name": "Core ETF",
            "fund_type": "ETF",
            "account_name": "Account A",
            "shares": "100",
            "cost_price": "1.0000",
            "current_nav": "2.0000",
            "tags": "",
            "note": "",
        },
        {
            "fund_code": "513100",
            "fund_name": "Overseas Fund",
            "fund_type": "QDII",
            "account_name": "Account B",
            "shares": "100",
            "cost_price": "2.0000",
            "tags": "",
            "note": "",
        },
    ]
    for payload in payloads:
        assert client.post("/api/v1/fund/positions", json=payload).status_code == 200

    response = client.get("/api/v1/fund/reports/daily")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["holding_summary"]["position_count"] == 2
    assert body["holding_summary"]["unrealized_profit"] == "100.0000"
    assert body["holding_summary"]["unrealized_return_rate"] == "1"
    assert body["allocation"]["total_amount"] == "400.0000"
    assert body["valuation_complete"] is False
    assert body["nav_age_days"] is None
    assert {alert["code"] for alert in body["alerts"]} == {
        "valuation_incomplete",
        "nav_missing",
        "holding_concentration",
        "watchlist_empty",
    }


def test_fund_watchlist_can_be_created_updated_and_deleted(client: TestClient) -> None:
    empty_summary_response = client.get("/api/v1/fund/watchlist/summary")
    assert empty_summary_response.status_code == 200
    assert empty_summary_response.json()["data"]["item_count"] == 0

    payload = {
        "fund_code": "159915",
        "fund_name": "创业板 ETF",
        "fund_type": "ETF",
        "priority": 2,
        "status": "watching",
        "watch_reason": "成长风格观察",
        "risk_level": "high",
        "target_position": "5%",
        "tags": "A股,成长",
        "note": "contract test",
    }
    create_response = client.post("/api/v1/fund/watchlist", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["fund_code"] == "159915"
    assert created["priority"] == 2
    assert created["risk_level"] == "high"

    list_response = client.get("/api/v1/fund/watchlist")
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    summary_response = client.get("/api/v1/fund/watchlist/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()["data"]
    assert summary["item_count"] == 1
    assert summary["high_priority_count"] == 1
    assert summary["risk_levels"] == ["high"]

    update_response = client.put(
        f"/api/v1/fund/watchlist/{created['id']}",
        json={**payload, "priority": 4, "status": "paused", "note": "updated"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["priority"] == 4
    assert updated["status"] == "paused"
    assert updated["note"] == "updated"

    delete_response = client.delete(f"/api/v1/fund/watchlist/{created['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"] == {"deleted": True, "id": created["id"]}

    final_summary_response = client.get("/api/v1/fund/watchlist/summary")
    assert final_summary_response.status_code == 200
    assert final_summary_response.json()["data"]["item_count"] == 0


def test_fund_nav_record_updates_matching_position_nav(client: TestClient) -> None:
    position_payload = {
        "fund_code": "513100",
        "fund_name": "纳指 ETF",
        "fund_type": "QDII",
        "account_name": "默认账户",
        "shares": "1000",
        "cost_price": "1.0000",
        "current_nav": "1.0000",
        "tags": "",
        "note": "",
    }
    position_response = client.post("/api/v1/fund/positions", json=position_payload)
    assert position_response.status_code == 200

    nav_payload = {
        "fund_code": "513100",
        "fund_name": "纳指 ETF",
        "fund_type": "QDII",
        "nav_date": "2026-07-28",
        "unit_nav": "1.2500",
        "accumulated_nav": "1.5000",
        "source": "manual",
        "note": "contract test",
    }
    nav_response = client.post("/api/v1/fund/nav-records", json=nav_payload)
    assert nav_response.status_code == 200
    created = nav_response.json()["data"]
    assert created["fund_code"] == "513100"
    assert created["unit_nav"] == "1.2500"

    list_response = client.get("/api/v1/fund/nav-records")
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    summary_response = client.get("/api/v1/fund/holdings/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()["data"]
    assert summary["current_value"] == "1250.0000"
    assert summary["unrealized_profit"] == "250.0000"

    upsert_response = client.post(
        "/api/v1/fund/nav-records",
        json={**nav_payload, "unit_nav": "1.3000", "note": "updated"},
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()["data"]["id"] == created["id"]
    assert upsert_response.json()["data"]["unit_nav"] == "1.3000"

    nav_summary_response = client.get("/api/v1/fund/nav-records/summary")
    assert nav_summary_response.status_code == 200
    nav_summary = nav_summary_response.json()["data"]
    assert nav_summary["record_count"] == 1
    assert nav_summary["latest_nav_date"] == "2026-07-28"

    delete_response = client.delete(f"/api/v1/fund/nav-records/{created['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"] == {"deleted": True, "id": created["id"]}


def test_current_dlt_rule_contract(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/rules/current")

    assert response.status_code == 200
    rule = response.json()["data"]
    assert rule["game_code"] == "dlt"
    assert rule["front"] == {"count": 5, "min": 1, "max": 35}
    assert rule["back"] == {"count": 2, "min": 1, "max": 12}
    assert rule["addon_supported"] is True
    assert len(rule["prize_tiers"]) == 13


def test_latest_draw_without_data_returns_domain_error(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/draws/latest")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "LOTTERY_DRAW_NOT_FOUND"


def test_sync_runs_endpoint_returns_empty_page(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/sync/runs")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["items"] == []
    assert body["pagination"]["total"] == 0


def test_sync_status_endpoint_returns_scheduler_state(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/sync/status")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["enabled"] is True
    assert body["running"] is True
    assert body["cron"] == "30 22 * * *"
    assert body["timezone"] == "Asia/Shanghai"
    assert body["page_size"] == 100
    assert body["latest_run"] is None


def test_basic_statistics_endpoint_returns_empty_statistics(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/statistics/basic")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["sample_size"] == 0
    assert body["requested_limit"] == 100
    assert body["stage_code"] is None
    assert body["stage_name"] is None
    assert len(body["front_frequency"]) == 35
    assert len(body["back_frequency"]) == 12
    assert body["sum"] == {"min": None, "max": None, "average": None}


def test_data_stage_endpoint_returns_empty_report(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/data/stages")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["sample_size"] == 0
    assert body["stages"] == []
    assert body["quality"]["level"] == "empty"
    assert {"warnings", "notes", "source_summary"}.issubset(body)


def test_data_stage_repair_endpoint_returns_contract(client: TestClient) -> None:
    response = client.post("/api/v1/lottery/dlt/data/stages/repair-rule-bindings")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["repaired_count"] == 0
    assert body["rule_code"] == "staged-rule-binding"
    assert body["stage_report"]["sample_size"] == 0


def test_randomness_endpoint_includes_deviation_diagnostics(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/statistics/randomness")

    assert response.status_code == 200
    body = response.json()["data"]
    assert {"level", "label", "description"}.issubset(body["sample_quality"])
    assert body["front_frequency"]["multiple_testing_tests"] == 35
    assert "adjusted_alpha" in body["front_frequency"]
    assert "significant_after_correction" in body["front_frequency"]
    front_deviation = body["front_frequency"]["top_deviations"][0]
    assert {
        "number",
        "count",
        "expected",
        "deviation",
        "confidence_low",
        "confidence_high",
        "z_score",
    }.issubset(front_deviation)
    assert front_deviation["confidence_low"] <= front_deviation["confidence_high"]


def test_decay_endpoint_returns_empty_contract(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/analysis/decay")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["sample_size"] == 0
    assert body["half_life"] == 50
    assert body["top"] == 10
    assert len(body["front"]["numbers"]) == 10
    assert len(body["back"]["numbers"]) == 10
    assert {
        "number",
        "raw_count",
        "weighted_count",
        "weighted_share",
        "raw_rank",
        "weighted_rank",
        "rank_delta",
    }.issubset(body["front"]["numbers"][0])


def test_co_occurrence_endpoint_includes_stage_contract(client: TestClient) -> None:
    response = client.get("/api/v1/lottery/dlt/analysis/co-occurrence")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["sample_size"] == 0
    assert body["stage_code"] is None
    assert body["stage_name"] is None
    assert {"nodes", "edges", "notes"}.issubset(body)


def test_saved_combination_can_be_created_and_listed(client: TestClient) -> None:
    payload = {
        "label": "回测池 1",
        "source": "test",
        "front_numbers": [5, 1, 3, 2, 4],
        "back_numbers": [2, 1],
        "favorite": True,
        "note": "contract test",
    }

    create_response = client.post("/api/v1/lottery/dlt/combinations", json=payload)

    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["label"] == "回测池 1"
    assert created["front_numbers"] == [1, 2, 3, 4, 5]
    assert created["back_numbers"] == [1, 2]
    assert created["favorite"] is True

    list_response = client.get("/api/v1/lottery/dlt/combinations")

    assert list_response.status_code == 200
    items = list_response.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == created["id"]


def test_saved_combination_upserts_same_numbers(client: TestClient) -> None:
    payload = {
        "label": "first",
        "source": "test",
        "front_numbers": [1, 2, 3, 4, 5],
        "back_numbers": [1, 2],
        "favorite": False,
        "note": "",
    }
    first_response = client.post("/api/v1/lottery/dlt/combinations", json=payload)
    second_response = client.post(
        "/api/v1/lottery/dlt/combinations",
        json={**payload, "label": "updated", "favorite": True},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["data"]["id"] == second_response.json()["data"]["id"]
    assert second_response.json()["data"]["label"] == "updated"

    list_response = client.get("/api/v1/lottery/dlt/combinations")
    assert len(list_response.json()["data"]) == 1
