from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from api.model_service import model_service
from api.schemas import (
    HealthResponse,
    ModelInfoResponse,
    PredictionRequest,
    PredictionResponse,
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


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(payload: PredictionRequest):
    try:
        prediction, localisation_grouped = model_service.predict(payload)

        return PredictionResponse(
            predicted_price_mad=round(prediction, 2),
            model_name=model_service.model_name,
            model_version=model_service.model_version,
            model_type=model_service.model_type,
            city=payload.city,
            localisation=payload.localisation,
            localisation_grouped=localisation_grouped,
        )

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
