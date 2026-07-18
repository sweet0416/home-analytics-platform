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
    assert len(body["front_frequency"]) == 35
    assert len(body["back_frequency"]) == 12
    assert body["sum"] == {"min": None, "max": None, "average": None}


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
