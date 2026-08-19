"""
Membre 7 - Monitoring : detection de derive simple (drift)
Compare la distribution des features d'un nouveau lot de donnees
a la baseline enregistree lors de l'entrainement (feature_baseline.json).

Utilise le PSI (Population Stability Index), une methode standard et
simple a interpreter :
    PSI < 0.1  -> pas de derive significative
    0.1-0.25   -> derive moderee, a surveiller
    > 0.25     -> derive importante, reentrainement a envisager

Usage:
    python ml/monitoring/drift_check.py --new-data data/nouvelles_annonces.csv
"""

import argparse
import json

import numpy as np
import pandas as pd

NUMERIC_FEATURES = ["surface_m2", "bedrooms", "bathrooms", "floor", "rooms"]
CATEGORICAL_FEATURES = ["city", "property_type", "localisation_grouped"]


def psi_numeric(baseline_stats: dict, new_values: pd.Series) -> float:
    """PSI pour une variable numerique, en reutilisant les vraies bornes/pourcentages
    de la distribution d'entrainement stockes dans feature_baseline.json."""
    edges = np.array(baseline_stats["bin_edges"], dtype=float)
    edges_for_hist = edges.copy()
    edges_for_hist[0], edges_for_hist[-1] = -np.inf, np.inf

    expected_pct = np.array(baseline_stats["bin_pct"])

    actual_counts, _ = np.histogram(new_values.dropna(), bins=edges_for_hist)
    actual_pct = actual_counts / max(actual_counts.sum(), 1)

    expected_pct = np.clip(expected_pct, 1e-4, None)
    actual_pct = np.clip(actual_pct, 1e-4, None)

    return float(
        np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    )


def psi_categorical(baseline_dist: dict, new_values: pd.Series) -> float:
    new_dist = new_values.value_counts(normalize=True).to_dict()
    categories = set(baseline_dist) | set(new_dist)

    psi = 0.0
    for cat in categories:
        expected = max(baseline_dist.get(cat, 0), 1e-4)
        actual = max(new_dist.get(cat, 0), 1e-4)
        psi += (actual - expected) * np.log(actual / expected)
    return float(psi)


def classify(psi: float) -> str:
    if psi < 0.1:
        return "OK"
    if psi < 0.25:
        return "MODERE"
    return "ALERTE"


def run_drift_check(baseline_path: str, new_data_path: str) -> pd.DataFrame:
    with open(baseline_path) as f:
        baseline = json.load(f)

    new_df = pd.read_csv(new_data_path)

    rows = []
    for col in NUMERIC_FEATURES:
        if col not in new_df.columns:
            continue
        score = psi_numeric(baseline["numeric"][col], new_df[col])
        rows.append(
            {"feature": col, "type": "numeric", "psi": score, "status": classify(score)}
        )

    for col in CATEGORICAL_FEATURES:
        if col not in new_df.columns:
            continue
        score = psi_categorical(baseline["categorical"][col], new_df[col])
        rows.append(
            {
                "feature": col,
                "type": "categorical",
                "psi": score,
                "status": classify(score),
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="feature_baseline.json")
    parser.add_argument("--new-data", required=True)
    args = parser.parse_args()

    report = run_drift_check(args.baseline, args.new_data)
    print(report.to_string(index=False))

    if (report["status"] == "ALERTE").any():
        print("\n⚠️  Derive importante detectee sur au moins une feature.")
    else:
        print("\n✅ Pas de derive significative detectee.")
