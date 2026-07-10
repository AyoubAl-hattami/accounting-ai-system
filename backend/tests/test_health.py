import os
import requests


BASE_URL = os.getenv("ACCOUNTING_TEST_BASE_URL", "http://127.0.0.1:8010")


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


def test_version_check():
    response = requests.get(f"{BASE_URL}/health/version")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["app_name"] == "Accounting AI System"
    assert data["environment"] == "development"
    assert data["version"] == "0.1.0"