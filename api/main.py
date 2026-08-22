import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException

from api.model_service import model_service
from api.schemas import (
    HealthResponse,
    ModelInfoResponse,
    PredictionRequest,
    PredictionResponse,
)

logger = logging.getLogger(__name__)

PREDICTION_LOG_PATH = os.getenv(
    "PREDICTION_LOG_PATH",
    "predictions.jsonl",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        model_service.ensure_loaded()
    except Exception as exc:  # noqa: BLE001
        print(f"Model not available at startup: {exc}")

    yield


app = FastAPI(
    title="Observatoire Intelligent des Prix Immobiliers",
    description=(
        "API de prédiction des prix immobiliers marocains "
        "avec modèle versionné via MLflow."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "service": "Observatoire Intelligent des Prix Immobiliers",
        "docs": "/docs",
        "health": "/health",
        "predict": "/predict",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health():
    try:
        model_service.ensure_loaded()

        return HealthResponse(
            status="healthy",
            model_loaded=True,
            model_name=model_service.model_name,
            model_version=model_service.model_version,
            model_type=model_service.model_type,
            tracking_uri=model_service.tracking_uri,
        )

    except Exception:  # noqa: BLE001
        return HealthResponse(
            status="waiting_for_model",
            model_loaded=False,
            model_name=model_service.model_name,
            tracking_uri=model_service.tracking_uri,
        )


@app.get(
    "/model-info",
    response_model=ModelInfoResponse,
)
def model_info():
    try:
        return ModelInfoResponse(**model_service.info())

    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )


@app.get("/supported-values")
def supported_values():
    try:
        model_service.ensure_loaded()

        return model_service.supported_values

    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )


def log_prediction(payload: PredictionRequest, response: PredictionResponse) -> None:
    log_path = Path(PREDICTION_LOG_PATH)

    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "surface_m2": payload.surface_m2,
        "bedrooms": payload.bedrooms,
        "bathrooms": payload.bathrooms,
        "floor": payload.floor,
        "rooms": payload.rooms,
        "city": payload.city,
        "property_type": payload.property_type,
        "localisation": payload.localisation,
        "localisation_grouped": response.localisation_grouped,
        "predicted_price_mad": response.predicted_price_mad,
        "model_name": response.model_name,
        "model_version": response.model_version,
        "model_type": response.model_type,
    }

    try:
        log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        with open(log_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Failed to write prediction monitoring log: %s", exc)


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(payload: PredictionRequest):
    try:
        prediction, localisation_grouped = model_service.predict(payload)

        response = PredictionResponse(
            predicted_price_mad=round(prediction, 2),
            model_name=model_service.model_name,
            model_version=model_service.model_version,
            model_type=model_service.model_type,
            city=payload.city,
            localisation=payload.localisation,
            localisation_grouped=localisation_grouped,
        )

        log_prediction(payload, response)

        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"Prediction service unavailable: {exc}",
        )
