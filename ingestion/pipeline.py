import csv
import os
import re
from pathlib import Path
from typing import Iterator, Dict, Any

import dlt
from dotenv import load_dotenv

load_dotenv()

DATA_FILE = Path(os.getenv("DATA_FILE", "data/housing_data.csv"))
PIPELINE_NAME = os.getenv("DLT_PIPELINE_NAME", "morocco_housing_ingestion")
DATASET_NAME = os.getenv("DLT_DATASET_NAME", "raw_immobilier")


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def to_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    # The source column names are preserved semantically but normalized
    # to SQL/Python-friendly snake_case names.
    return {
        "listing_id": to_int(row.get("Unnamed: 0")),
        "price_mad": to_int(row.get("new_price")),
        "description": clean_text(row.get("desc")),
        "address": clean_text(row.get("address")),
        "bedrooms": to_int(row.get("chambres")),
        "bathrooms": to_int(row.get("salles de bains")),
        "surface_m2": to_int(row.get("surface")),
        "elevator": clean_text(row.get("ascenseur")),
        "floor": to_int(row.get("floor")),
        "terrace": clean_text(row.get("terrasse")),
        "parking": clean_text(row.get("parking")),
        "property_type": clean_text(row.get("Type")),
        "city": clean_text(row.get("City")),
        "neighborhood": clean_text(row.get("Nighberd")),
        "source": "kaggle_morocco_housing",
    }


@dlt.resource(
    name="housing_listings",
    write_disposition="merge",
    primary_key="listing_id",
    columns={
        "listing_id": {"data_type": "bigint"},
        "price_mad": {"data_type": "bigint"},
        "surface_m2": {"data_type": "bigint"},
        "bedrooms": {"data_type": "bigint"},
        "bathrooms": {"data_type": "bigint"},
        "floor": {"data_type": "bigint"},
    },
)
def housing_listings() -> Iterator[Dict[str, Any]]:
    with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield normalize_row(row)


def main():
    pipeline = dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination="duckdb",
        dataset_name=DATASET_NAME,
    )

    load_info = pipeline.run(housing_listings())
    print(load_info)


if __name__ == "__main__":
    main()
