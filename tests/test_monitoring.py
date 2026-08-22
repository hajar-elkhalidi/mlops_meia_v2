import json
from types import SimpleNamespace

import pandas as pd
from fastapi.testclient import TestClient

from monitoring import service
from monitoring.main import app


def test_monitoring_health():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_empty_availability_history(tmp_path):
    records = service.read_jsonl(tmp_path / "missing.jsonl")
    summary = service.summarize_availability(records)

    assert records == []
    assert summary["api_available"] is None
    assert summary["checks_total"] == 0
    assert summary["uptime_percentage"] is None
    assert summary["average_latency_ms"] is None


def test_availability_calculations():
    records = [
        {"available": True, "latency_ms": 10.0},
        {"available": False, "latency_ms": 20.0},
        {"available": True, "latency_ms": 30.0},
    ]

    summary = service.summarize_availability(records)

    assert summary["api_available"] is True
    assert summary["checks_total"] == 3
    assert summary["checks_successful"] == 2
    assert summary["uptime_percentage"] == 66.67
    assert summary["latest_latency_ms"] == 30.0
    assert summary["average_latency_ms"] == 20.0
    assert summary["p95_latency_ms"] == 30.0


def test_prediction_jsonl_parsing_skips_malformed_lines(tmp_path):
    log_path = tmp_path / "predictions.jsonl"
    log_path.write_text(
        '{"surface_m2": 100}\nnot-json\n[]\n{"city": "Casablanca"}\n',
        encoding="utf-8",
    )

    records = service.read_jsonl(log_path)

    assert records == [
        {"surface_m2": 100},
        {"city": "Casablanca"},
    ]


def test_insufficient_drift_samples(tmp_path):
    baseline_path = tmp_path / "feature_baseline.json"
    prediction_path = tmp_path / "predictions.jsonl"
    baseline_path.write_text("{}", encoding="utf-8")
    service.append_jsonl(prediction_path, {"surface_m2": 100})

    report = service.get_drift_report(
        baseline_path=baseline_path,
        prediction_log_path=prediction_path,
        minimum_samples=20,
    )

    assert report["status"] == "insufficient_data"
    assert report["samples_analyzed"] == 1
    assert report["minimum_required"] == 20
    assert report["drift_detected"] is False


def test_numeric_psi_stable_synthetic_data():
    baseline = {
        "bin_edges": [0, 1, 2, 3],
        "bin_pct": [1 / 3, 1 / 3, 1 / 3],
    }

    score = service.psi_numeric(
        baseline,
        pd.Series([0.2, 0.5, 1.2, 1.5, 2.2, 2.5]),
    )

    assert score < 0.10
    assert service.classify_psi(score) == "stable"


def test_numeric_psi_shifted_synthetic_data():
    baseline = {
        "bin_edges": [0, 1, 2, 3],
        "bin_pct": [1 / 3, 1 / 3, 1 / 3],
    }

    score = service.psi_numeric(
        baseline,
        pd.Series([5, 6, 7, 8, 9, 10]),
    )

    assert score >= 0.25
    assert service.classify_psi(score) == "significant"


def test_categorical_psi_calculation():
    baseline = {
        "Appartement": 0.5,
        "Villa": 0.5,
    }

    stable_score = service.psi_categorical(
        baseline,
        pd.Series(["Appartement", "Villa", "Appartement", "Villa"]),
    )
    shifted_score = service.psi_categorical(
        baseline,
        pd.Series(["Terrain", "Terrain", "Terrain", "Terrain"]),
    )

    assert stable_score < 0.10
    assert shifted_score >= 0.25


def test_metrics_survives_mlflow_unavailable(tmp_path, monkeypatch):
    availability_path = tmp_path / "availability.jsonl"
    service.append_jsonl(
        availability_path,
        {
            "available": True,
            "latency_ms": 25.0,
            "status_code": 200,
        },
    )

    class BrokenMlflowClient:
        def get_model_version_by_alias(self, name, alias):
            raise RuntimeError("mlflow unavailable")

    monkeypatch.setattr(service, "AVAILABILITY_LOG_PATH", str(availability_path))
    monkeypatch.setattr(service.mlflow, "set_tracking_uri", lambda uri: None)
    monkeypatch.setattr(service, "MlflowClient", BrokenMlflowClient)

    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["service"]["checks_total"] == 1
    assert data["model"]["available"] is False
    assert "mlflow unavailable" in data["model"]["error"]


def test_model_metrics_success(monkeypatch):
    model_version = SimpleNamespace(
        version="7",
        run_id="abc123",
    )
    run = SimpleNamespace(
        data=SimpleNamespace(
            metrics={
                "rmse": 1000.0,
                "mae": 500.0,
                "r2": 0.91,
                "other": 1.0,
            }
        )
    )

    class FakeMlflowClient:
        def get_model_version_by_alias(self, name, alias):
            return model_version

        def get_run(self, run_id):
            return run

    monkeypatch.setattr(service.mlflow, "set_tracking_uri", lambda uri: None)
    monkeypatch.setattr(service, "MlflowClient", FakeMlflowClient)

    metrics = service.get_model_metrics()

    assert metrics["available"] is True
    assert metrics["version"] == "7"
    assert metrics["run_id"] == "abc123"
    assert metrics["metrics"] == {
        "rmse": 1000.0,
        "mae": 500.0,
        "r2": 0.91,
    }


def test_drift_report_with_enough_samples(tmp_path):
    baseline = {
        "numeric": {
            "surface_m2": {
                "bin_edges": [0, 100, 200, 300],
                "bin_pct": [1 / 3, 1 / 3, 1 / 3],
            }
        },
        "categorical": {
            "city": {
                "Casablanca": 1.0,
            }
        },
    }
    baseline_path = tmp_path / "feature_baseline.json"
    prediction_path = tmp_path / "predictions.jsonl"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

    for surface in [50, 75, 150, 175, 250, 275]:
        service.append_jsonl(
            prediction_path,
            {
                "surface_m2": surface,
                "city": "Casablanca",
            },
        )

    report = service.get_drift_report(
        baseline_path=baseline_path,
        prediction_log_path=prediction_path,
        minimum_samples=6,
    )

    assert report["status"] == "ok"
    assert report["samples_analyzed"] == 6
    assert report["drift_detected"] is False
    assert report["features"]["surface_m2"]["status"] == "stable"
