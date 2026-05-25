import requests


BASE_URL = "http://127.0.0.1:8010"


def test_health_check():
    response = requests.get(f"{BASE_URL}/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "accounting-ai-backend"


def test_database_health_check():
    response = requests.get(f"{BASE_URL}/health/db")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["database"] == "connected"