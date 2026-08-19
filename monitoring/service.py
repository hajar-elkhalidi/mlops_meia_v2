import asyncio
import json
import logging
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from ml.monitoring.drift_check import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    psi_categorical,
    psi_numeric,
)

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
REGISTERED_MODEL_NAME = os.getenv("REGISTERED_MODEL_NAME", "prix_immobilier_maroc")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "champion")
FEATURE_BASELINE_PATH = os.getenv("FEATURE_BASELINE_PATH", "feature_baseline.json")
PREDICTION_LOG_PATH = os.getenv("PREDICTION_LOG_PATH", "predictions.jsonl")
AVAILABILITY_LOG_PATH = os.getenv("AVAILABILITY_LOG_PATH", "availability.jsonl")
MONITOR_INTERVAL_SECONDS = float(os.getenv("MONITOR_INTERVAL_SECONDS", "30"))
DRIFT_MIN_SAMPLES = int(os.getenv("DRIFT_MIN_SAMPLES", "20"))


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(log_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    log_path = Path(path)

    if not log_path.exists():
        return []

    records = []
    with open(log_path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(record, dict):
                records.append(record)

    return records


async def probe_api_health() -> dict[str, Any]:
    status_code = None
    available = False
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
        status_code = response.status_code
        available = response.status_code == 200
    except httpx.HTTPError as exc:
        logger.warning("API health probe failed: %s", exc)

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    record = {
        "timestamp": utc_timestamp(),
        "available": available,
        "status_code": status_code,
        "latency_ms": latency_ms,
    }

    try:
        append_jsonl(AVAILABILITY_LOG_PATH, record)
    except OSError as exc:
        logger.warning("Failed to write availability monitoring log: %s", exc)

    return record


async def availability_monitor_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=MONITOR_INTERVAL_SECONDS,
            )
        except TimeoutError:
            pass

        if stop_event.is_set():
            break

        try:
            await probe_api_health()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Availability monitoring iteration failed: %s", exc)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None

    sorted_values = sorted(values)
    index = math.ceil((pct / 100) * len(sorted_values)) - 1
    index = max(0, min(index, len(sorted_values) - 1))
    return round(sorted_values[index], 2)


def summarize_availability(records: list[dict[str, Any]]) -> dict[str, Any]:
    checks_total = len(records)
    successful = [record for record in records if record.get("available") is True]
    latencies = [
        float(record["latency_ms"])
        for record in records
        if isinstance(record.get("latency_ms"), int | float)
    ]
    latest = records[-1] if records else {}

    uptime_percentage = (
        round((len(successful) / checks_total) * 100, 2) if checks_total else None
    )
    average_latency_ms = (
        round(sum(latencies) / len(latencies), 2) if latencies else None
    )

    return {
        "api_available": latest.get("available"),
        "checks_total": checks_total,
        "checks_successful": len(successful),
        "uptime_percentage": uptime_percentage,
        "latest_latency_ms": latest.get("latency_ms"),
        "average_latency_ms": average_latency_ms,
        "p95_latency_ms": percentile(latencies, 95),
    }


def get_model_metrics() -> dict[str, Any]:
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = MlflowClient()
        model_version = client.get_model_version_by_alias(
            REGISTERED_MODEL_NAME,
            MODEL_ALIAS,
        )
        run = client.get_run(model_version.run_id)

        return {
            "available": True,
            "name": REGISTERED_MODEL_NAME,
            "version": str(model_version.version),
            "alias": MODEL_ALIAS,
            "run_id": model_version.run_id,
            "metrics": {
                key: run.data.metrics[key]
                for key in ("rmse", "mae", "r2")
                if key in run.data.metrics
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("MLflow model metrics unavailable: %s", exc)
        return {
            "available": False,
            "name": REGISTERED_MODEL_NAME,
            "alias": MODEL_ALIAS,
            "error": str(exc),
            "metrics": {},
        }


def get_metrics() -> dict[str, Any]:
    return {
        "service": summarize_availability(read_jsonl(AVAILABILITY_LOG_PATH)),
        "model": get_model_metrics(),
    }


def classify_psi(score: float) -> str:
    if score < 0.10:
        return "stable"
    if score < 0.25:
        return "moderate"
    return "significant"


def load_baseline(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def build_feature_result(
    feature: str, feature_type: str, score: float
) -> dict[str, Any]:
    status = classify_psi(score)
    return {
        "feature": feature,
        "type": feature_type,
        "psi": round(score, 6),
        "status": status,
    }


def get_drift_report(
    baseline_path: str | Path = FEATURE_BASELINE_PATH,
    prediction_log_path: str | Path = PREDICTION_LOG_PATH,
    minimum_samples: int = DRIFT_MIN_SAMPLES,
) -> dict[str, Any]:
    records = read_jsonl(prediction_log_path)
    samples_analyzed = len(records)

    baseline_file = Path(baseline_path)
    if not baseline_file.exists():
        return {
            "status": "baseline_missing",
            "baseline_path": str(baseline_file),
            "samples_analyzed": samples_analyzed,
            "drift_detected": False,
            "features": {},
        }

    if samples_analyzed < minimum_samples:
        return {
            "status": "insufficient_data",
            "samples_analyzed": samples_analyzed,
            "minimum_required": minimum_samples,
            "drift_detected": False,
            "features": {},
        }

    baseline = load_baseline(baseline_file)
    production = pd.DataFrame(records)
    features = {}

    for feature in NUMERIC_FEATURES:
        if feature not in production.columns or feature not in baseline.get(
            "numeric", {}
        ):
            continue

        score = psi_numeric(baseline["numeric"][feature], production[feature])
        features[feature] = build_feature_result(feature, "numeric", score)

    for feature in CATEGORICAL_FEATURES:
        if feature not in production.columns or feature not in baseline.get(
            "categorical", {}
        ):
            continue

        score = psi_categorical(baseline["categorical"][feature], production[feature])
        features[feature] = build_feature_result(feature, "categorical", score)

    statuses = {result["status"] for result in features.values()}
    drift_detected = "significant" in statuses
    status = "drift_detected" if drift_detected else "ok"

    if not drift_detected and "moderate" in statuses:
        status = "warning"

    return {
        "status": status,
        "samples_analyzed": samples_analyzed,
        "minimum_required": minimum_samples,
        "drift_detected": drift_detected,
        "features": features,
    }
