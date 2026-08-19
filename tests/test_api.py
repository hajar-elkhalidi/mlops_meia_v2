import json

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app
from api.model_service import model_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def prediction_log_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        api_main,
        "PREDICTION_LOG_PATH",
        str(tmp_path / "predictions.jsonl"),
    )


def configure_fake_model(monkeypatch):
    monkeypatch.setattr(
        model_service,
        "ensure_loaded",
        lambda: None,
    )

    monkeypatch.setattr(
        model_service,
        "model_version",
        "1",
    )

    monkeypatch.setattr(
        model_service,
        "model_type",
        "LinearRegression",
    )


def test_health(monkeypatch):
    configure_fake_model(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_name"] == "prix_immobilier_maroc"
    assert data["model_version"] == "1"


def test_predict(monkeypatch, tmp_path):
    configure_fake_model(monkeypatch)

    monkeypatch.setattr(
        model_service,
        "predict",
        lambda payload: (2_500_000.0, "Ain Diab"),
    )

    response = client.post(
        "/predict",
        json={
            "surface_m2": 100,
            "bedrooms": 2,
            "bathrooms": 1,
            "floor": 2,
            "rooms": 3,
            "city": "Casablanca",
            "property_type": "Appartement",
            "localisation": "Ain Diab",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["predicted_price_mad"] == 2_500_000.0
    assert data["model_name"] == "prix_immobilier_maroc"
    assert data["model_version"] == "1"
    assert data["localisation_grouped"] == "Ain Diab"

    records = [
        json.loads(line)
        for line in (tmp_path / "predictions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert len(records) == 1
    assert records[0]["surface_m2"] == 100
    assert records[0]["predicted_price_mad"] == 2_500_000.0
    assert records[0]["model_type"] == "LinearRegression"


def test_invalid_surface():
    response = client.post(
        "/predict",
        json={
            "surface_m2": -50,
            "bedrooms": 2,
            "bathrooms": 1,
            "floor": 2,
            "rooms": 3,
            "city": "Casablanca",
            "property_type": "Appartement",
            "localisation": "Ain Diab",
        },
    )

    assert response.status_code == 422
