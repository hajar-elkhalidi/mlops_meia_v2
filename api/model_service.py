import os
from threading import Lock

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient


class ModelService:
    def __init__(self):
        self.tracking_uri = os.getenv(
            "MLFLOW_TRACKING_URI",
            "sqlite:///mlflow.db",
        )

        self.model_name = os.getenv(
            "REGISTERED_MODEL_NAME",
            "prix_immobilier_maroc",
        )

        self.model_alias = os.getenv(
            "MODEL_ALIAS",
            "champion",
        )

        self.model = None
        self.model_version = None
        self.model_type = None

        self.supported_values = {}
        self._lock = Lock()

        mlflow.set_tracking_uri(self.tracking_uri)

    def _resolve_version(self):
        client = MlflowClient()

        try:
            version = client.get_model_version_by_alias(
                self.model_name,
                self.model_alias,
            )

            return str(version.version), (
                f"models:/{self.model_name}@{self.model_alias}"
            )

        except MlflowException:
            versions = client.search_model_versions(f"name='{self.model_name}'")

            if not versions:
                raise RuntimeError(
                    f"No registered version found for "
                    f"'{self.model_name}'. Run training first."
                )

            latest = max(
                versions,
                key=lambda item: int(item.version),
            )

            return str(latest.version), (f"models:/{self.model_name}/{latest.version}")

    def ensure_loaded(self):
        version, model_uri = self._resolve_version()

        if self.model is not None and self.model_version == version:
            return

        with self._lock:
            if self.model is not None and self.model_version == version:
                return

            model = mlflow.sklearn.load_model(model_uri)

            self.model = model
            self.model_version = version

            estimator = model.named_steps["model"]
            self.model_type = type(estimator).__name__

            self._extract_supported_values()

    def _extract_supported_values(self):
        preprocessor = self.model.named_steps["preprocessing"]

        encoder = preprocessor.named_transformers_["cat"]

        categories = encoder.categories_

        self.supported_values = {
            "city": [str(value) for value in categories[0]],
            "property_type": [str(value) for value in categories[1]],
            "localisation_grouped": [str(value) for value in categories[2]],
        }

    def _prepare_input(self, payload):
        cities = self.supported_values["city"]
        property_types = self.supported_values["property_type"]
        locations = self.supported_values["localisation_grouped"]

        if payload.city not in cities:
            raise ValueError(
                f"Unsupported city '{payload.city}'. "
                f"Supported cities: {', '.join(cities)}"
            )

        if payload.property_type not in property_types:
            raise ValueError(
                f"Unsupported property_type "
                f"'{payload.property_type}'. "
                f"Supported values: "
                f"{', '.join(property_types)}"
            )

        localisation_grouped = (
            payload.localisation if payload.localisation in locations else "Autre"
        )

        row = {
            "surface_m2": payload.surface_m2,
            "bedrooms": payload.bedrooms,
            "bathrooms": payload.bathrooms,
            "floor": payload.floor,
            "rooms": payload.rooms,
            "city": payload.city,
            "property_type": payload.property_type,
            "localisation_grouped": localisation_grouped,
        }

        return pd.DataFrame([row]), localisation_grouped

    def predict(self, payload):
        self.ensure_loaded()

        frame, localisation_grouped = self._prepare_input(payload)

        prediction = float(self.model.predict(frame)[0])

        return prediction, localisation_grouped

    def info(self):
        self.ensure_loaded()

        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "alias": self.model_alias,
            "tracking_uri": self.tracking_uri,
        }


model_service = ModelService()
