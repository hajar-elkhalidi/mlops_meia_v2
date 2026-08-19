"""
Membre 7 - ML Engineer 2 (Tracking & Registry)
Reprend le pipeline de modelisation de membre 6 (stg_housing_listings)
et ajoute : MLflow experiment tracking + model registry + baseline
de features pour la detection de derive.

Usage:
    python ml/tracking/train_with_mlflow.py
"""
import json
import os

import duckdb
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

# ---------------------------------------------------------------------
# 0. CONFIG - adapte ces chemins/noms a ton .env si besoin
# ---------------------------------------------------------------------
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    "morocco_housing_ingestion.duckdb",
)
SOURCE_TABLE = os.getenv(
    "SOURCE_TABLE",
    "stg_housing_listings",
)
MLFLOW_EXPERIMENT = os.getenv(
    "MLFLOW_EXPERIMENT",
    "observatoire_prix_immobiliers",
)
REGISTERED_MODEL_NAME = os.getenv(
    "REGISTERED_MODEL_NAME",
    "prix_immobilier_maroc",
)
MODEL_ALIAS = os.getenv(
    "MODEL_ALIAS",
    "champion",
)
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "sqlite:///mlflow.db",
)
RARE_LOCALISATION_THRESHOLD = 5
PRICE_MIN, PRICE_MAX = 50_000, 30_000_000

NUMERIC_FEATURES = ["surface_m2", "bedrooms", "bathrooms", "floor", "rooms"]
CATEGORICAL_FEATURES = ["city", "property_type", "localisation_grouped"]
TARGET = "price_mad"


# ---------------------------------------------------------------------
# 1. CHARGEMENT + PREPARATION DES DONNEES (reprend le rapport membre 6)
# ---------------------------------------------------------------------
def load_and_prepare_data() -> pd.DataFrame:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    df = con.execute(f"SELECT * FROM {SOURCE_TABLE}").fetchdf()
    con.close()

    # prix manquant / doublons
    df = df.dropna(subset=[TARGET]).drop_duplicates()

    # valeurs de prix aberrantes
    df = df[(df[TARGET] >= PRICE_MIN) & (df[TARGET] <= PRICE_MAX)]

    # colonnes quasi vides / fuite de donnees
    cols_to_drop = [
        c
        for c in ["address", "elevator", "terrace", "parking", "price_per_sqm_calculated"]
        if c in df.columns
    ]
    df = df.drop(columns=cols_to_drop)

    # imputation mediane de 'rooms'
    if df["rooms"].isna().any():
        df["rooms"] = df["rooms"].fillna(df["rooms"].median())

    # regroupement des localisations rares
    counts = df["localisation"].value_counts()
    frequent = counts[counts > RARE_LOCALISATION_THRESHOLD].index
    df["localisation_grouped"] = df["localisation"].where(
        df["localisation"].isin(frequent), "Autre"
    )

    keep = NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET]
    return df[keep].dropna(subset=NUMERIC_FEATURES)


# ---------------------------------------------------------------------
# 2. PIPELINE SCIKIT-LEARN (pretraitement + estimateur)
# ---------------------------------------------------------------------
def build_pipeline(estimator) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[("preprocessing", preprocessor), ("model", estimator)])


def evaluate(y_true, y_pred) -> dict:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


# ---------------------------------------------------------------------
# 3. ENTRAINEMENT + LOGGING MLFLOW POUR LES 3 MODELES
# ---------------------------------------------------------------------
def main():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    df = load_and_prepare_data()
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    models = {
        "linear_regression": (LinearRegression(), {}),
        "random_forest": (
            RandomForestRegressor(n_estimators=200, random_state=42),
            {"n_estimators": 200, "random_state": 42},
        ),
        "xgboost": (
            XGBRegressor(n_estimators=300, learning_rate=0.05, random_state=42),
            {"n_estimators": 300, "learning_rate": 0.05, "random_state": 42},
        ),
    }

    results = {}
    best_run_id, best_model_name, best_r2 = None, None, -np.inf

    for name, (estimator, params) in models.items():
        with mlflow.start_run(run_name=name) as run:
            pipe = build_pipeline(estimator)
            pipe.fit(X_train, y_train)
            preds = pipe.predict(X_test)
            metrics = evaluate(y_test, preds)

            mlflow.log_param("model_type", name)
            for k, v in params.items():
                mlflow.log_param(k, v)
            mlflow.log_params(
                {"train_size": len(X_train), "test_size": len(X_test), "random_state": 42}
            )
            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(
                pipe,
                artifact_path="model",
                serialization_format="pickle",  # skops (default) doesn't trust xgboost's internal types
            )

            results[name] = metrics
            print(f"[{name}] RMSE={metrics['rmse']:.0f}  MAE={metrics['mae']:.0f}  R2={metrics['r2']:.3f}")

            if metrics["r2"] > best_r2:
                best_r2 = metrics["r2"]
                best_run_id = run.info.run_id
                best_model_name = name

    # comparatif des 3 modeles en artifact (comme comparaison_modeles.csv de membre 6)
    comp_df = pd.DataFrame(results).T
    comp_path = "comparaison_modeles.csv"
    comp_df.to_csv(comp_path)
    with mlflow.start_run(run_name="comparison_summary"):
        mlflow.log_artifact(comp_path)

    print(f"\nMeilleur modele : {best_model_name} (R2={best_r2:.3f}), run_id={best_run_id}")

    # -------------------------------------------------------------
    # 4. ENREGISTREMENT DANS LE MODEL REGISTRY
    # -------------------------------------------------------------
    model_uri = f"runs:/{best_run_id}/model"
    registered = mlflow.register_model(model_uri=model_uri, name=REGISTERED_MODEL_NAME)
    print(f"Modele enregistre : {REGISTERED_MODEL_NAME} v{registered.version}")

    client = mlflow.MlflowClient()
    client.transition_model_version_stage(
        name=REGISTERED_MODEL_NAME,
        version=registered.version,
        stage="Staging",
    )
    client.set_registered_model_alias(
        name=REGISTERED_MODEL_NAME,
        alias=MODEL_ALIAS,
        version=registered.version,
    )
    client.update_model_version(
        name=REGISTERED_MODEL_NAME,
        version=registered.version,
        description=(
            f"Modele {best_model_name} retenu (RMSE={results[best_model_name]['rmse']:.0f}, "
            f"MAE={results[best_model_name]['mae']:.0f}, R2={results[best_model_name]['r2']:.3f}). "
            "Voir rapport membre 6 pour le detail du preprocessing."
        ),
    )

    # -------------------------------------------------------------
    # 5. BASELINE DE FEATURES POUR LA DETECTION DE DERIVE (membre 7)
    # -------------------------------------------------------------
    N_BINS = 10

    def numeric_baseline(col: str) -> dict:
        col_min, col_max = float(X_train[col].min()), float(X_train[col].max())
        edges = np.linspace(col_min, col_max, N_BINS + 1)
        edges_for_hist = edges.copy()
        edges_for_hist[0], edges_for_hist[-1] = -np.inf, np.inf
        counts, _ = np.histogram(X_train[col].dropna(), bins=edges_for_hist)
        pct = (counts / counts.sum()).tolist()
        return {
            "mean": float(X_train[col].mean()),
            "std": float(X_train[col].std()),
            "min": col_min,
            "p25": float(X_train[col].quantile(0.25)),
            "p50": float(X_train[col].quantile(0.50)),
            "p75": float(X_train[col].quantile(0.75)),
            "max": col_max,
            "bin_edges": edges.tolist(),
            "bin_pct": pct,
        }

    baseline = {
        "numeric": {col: numeric_baseline(col) for col in NUMERIC_FEATURES},
        "categorical": {
            col: X_train[col].value_counts(normalize=True).to_dict()
            for col in CATEGORICAL_FEATURES
        },
    }
    baseline_path = "feature_baseline.json"
    with open(baseline_path, "w") as f:
        json.dump(baseline, f, indent=2)

    with mlflow.start_run(run_name="feature_baseline"):
        mlflow.log_artifact(baseline_path)

    print(f"Baseline de features sauvegardee -> {baseline_path}")


if __name__ == "__main__":
    main()
