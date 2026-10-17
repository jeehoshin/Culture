from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json()["status"] == "ok"


def test_filter_free_exhibitions() -> None:
    response = client.get("/api/v1/events", params={"category": "exhibition", "price": "free"})
    assert response.status_code == 200
    assert all(item["category"] == "exhibition" for item in response.json()["items"])
    assert all(item["price_type"] == "free" for item in response.json()["items"])
