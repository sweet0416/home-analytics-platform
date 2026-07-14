from fastapi.testclient import TestClient


def test_health_check_returns_standard_response(client: TestClient) -> None:
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["code"] == "OK"
    assert body["data"]["status"] == "ok"
    assert "x-trace-id" in response.headers


def test_plugins_endpoint_returns_lottery_plugin(client: TestClient) -> None:
    response = client.get("/api/v1/plugins")

    assert response.status_code == 200
    plugins = response.json()["data"]
    assert any(plugin["name"] == "lottery" for plugin in plugins)


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
