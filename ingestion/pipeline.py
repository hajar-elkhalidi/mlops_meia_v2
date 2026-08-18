import csv
import os
from pathlib import Path
from typing import Iterator, Dict, Any

import dlt
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# Configuration
# ============================================================

MOROCCO_DATA_FILE = Path(
    os.getenv(
        "MOROCCO_DATA_FILE",
        "data/housing_data.csv",
    )
)

CASA_DATA_FILE = Path(
    os.getenv(
        "CASA_DATA_FILE",
        "data/casa_housing.csv",
    )
)

PIPELINE_NAME = os.getenv(
    "DLT_PIPELINE_NAME",
    "morocco_housing_ingestion",
)

DATASET_NAME = os.getenv(
    "DLT_DATASET_NAME",
    "raw_immobilier",
)

# Local default:
#   morocco_housing_ingestion.duckdb
#
# Docker / Komodo:
#   /runtime/data/morocco_housing_ingestion.duckdb
DUCKDB_PATH = Path(
    os.getenv(
        "DUCKDB_PATH",
        "morocco_housing_ingestion.duckdb",
    )
)


# ============================================================
# Helpers
# ============================================================

def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def to_int(value: Any) -> int | None:
    if value is None:
        return None

    raw_value = str(value).strip()

    if raw_value == "":
        return None

    try:
        return int(
            float(
                raw_value.replace(",", "")
            )
        )
    except (ValueError, TypeError):
        return None


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    raw_value = str(value).strip()

    if raw_value == "":
        return None

    try:
        return float(
            raw_value.replace(",", "")
        )
    except (ValueError, TypeError):
        return None


# ============================================================
# Morocco dataset
# ============================================================

def normalize_morocco_row(
    row: Dict[str, Any],
    source_listing_id: int,
) -> Dict[str, Any]:

    # In the original Morocco CSV the first column
    # may have an empty header.
    raw_id = (
        row.get("listing_id")
        or row.get("Unnamed: 0")
        or row.get("")
    )

    source_id = to_int(raw_id)

    # If the cleaned file no longer contains the original index,
    # use the row number as a stable source identifier.
    if source_id is None:
        source_id = source_listing_id

    price = to_int(
        row.get("new_price")
    )

    surface = to_float(
        row.get("surface")
    )

    price_m2 = None

    if (
        price is not None
        and surface is not None
        and surface > 0
    ):
        price_m2 = round(
            price / surface,
            2,
        )

    return {
        "listing_id": f"morocco_{source_id}",
        "source_listing_id": source_id,

        "price_mad": price,
        "surface_m2": surface,
        "price_m2": price_m2,

        "rooms": None,

        "bedrooms": to_int(
            row.get("chambres")
        ),

        "bathrooms": to_int(
            row.get("salles de bains")
        ),

        "floor": to_int(
            row.get("floor")
        ),

        "address": clean_text(
            row.get("address")
        ),

        "localisation": clean_text(
            row.get("Nighberd")
            or row.get("address")
        ),

        "elevator": clean_text(
            row.get("ascenseur")
        ),

        "terrace": clean_text(
            row.get("terrasse")
        ),

        "parking": clean_text(
            row.get("parking")
        ),

        "other_tags": None,

        "property_type": clean_text(
            row.get("Type")
        ),

        "city": clean_text(
            row.get("City")
        ),

        "source": "kaggle_morocco_housing",
    }


# ============================================================
# Casablanca dataset
# ============================================================

def normalize_casa_row(
    row: Dict[str, Any],
    source_listing_id: int,
) -> Dict[str, Any]:

    price = to_float(
        row.get("Price")
    )

    surface = to_float(
        row.get("Area")
    )

    source_price_m2 = to_float(
        row.get("Price_m2")
    )

    calculated_price_m2 = None

    if (
        price is not None
        and surface is not None
        and surface > 0
    ):
        calculated_price_m2 = round(
            price / surface,
            2,
        )

    return {
        "listing_id": f"casa_{source_listing_id}",
        "source_listing_id": source_listing_id,

        "price_mad": price,
        "surface_m2": surface,

        "price_m2": (
            source_price_m2
            if source_price_m2 is not None
            else calculated_price_m2
        ),

        "rooms": to_int(
            row.get("Rooms")
        ),

        "bedrooms": to_int(
            row.get("Bedrooms")
        ),

        "bathrooms": to_int(
            row.get("Bathrooms")
        ),

        "floor": to_int(
            row.get("Floor")
        ),

        "address": None,

        "localisation": clean_text(
            row.get("Localisation")
        ),

        "elevator": None,
        "terrace": None,
        "parking": None,

        "other_tags": clean_text(
            row.get("Other_tags")
        ),

        "property_type": clean_text(
            row.get("Type")
        ),

        "city": "Casablanca",

        "source": "casa_housing",
    }


# ============================================================
# dlt resource
# ============================================================

@dlt.resource(
    name="housing_listings",
    write_disposition="merge",
    primary_key="listing_id",
    columns={
        "listing_id": {
            "data_type": "text",
            "nullable": False,
        },
        "source_listing_id": {
            "data_type": "bigint",
        },
        "price_mad": {
            "data_type": "double",
        },
        "surface_m2": {
            "data_type": "double",
        },
        "price_m2": {
            "data_type": "double",
        },
        "rooms": {
            "data_type": "bigint",
        },
        "bedrooms": {
            "data_type": "bigint",
        },
        "bathrooms": {
            "data_type": "bigint",
        },
        "floor": {
            "data_type": "bigint",
        },
    },
)
def housing_listings() -> Iterator[Dict[str, Any]]:

    if not MOROCCO_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Morocco dataset not found: "
            f"{MOROCCO_DATA_FILE.resolve()}"
        )

    if not CASA_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Casablanca dataset not found: "
            f"{CASA_DATA_FILE.resolve()}"
        )

    # Morocco dataset
    with MOROCCO_DATA_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            yield normalize_morocco_row(
                row,
                row_number,
            )

    # Casablanca dataset
    with CASA_DATA_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            yield normalize_casa_row(
                row,
                row_number,
            )


# ============================================================
# Pipeline
# ============================================================

def main() -> None:

    # Ensure the target directory exists.
    #
    # Local:
    #   .
    #
    # Docker:
    #   /runtime/data/
    DUCKDB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"[INFO] Pipeline name: {PIPELINE_NAME}"
    )

    print(
        f"[INFO] Dataset name: {DATASET_NAME}"
    )

    print(
        f"[INFO] DuckDB path: {DUCKDB_PATH.resolve()}"
    )

    print(
        f"[INFO] Morocco dataset: "
        f"{MOROCCO_DATA_FILE.resolve()}"
    )

    print(
        f"[INFO] Casablanca dataset: "
        f"{CASA_DATA_FILE.resolve()}"
    )

    # Important:
    # explicitly give dlt the exact DuckDB path.
    destination = dlt.destinations.duckdb(
        str(DUCKDB_PATH)
    )

    pipeline = dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination=destination,
        dataset_name=DATASET_NAME,
    )

    load_info = pipeline.run(
        housing_listings()
    )

    print(load_info)


if __name__ == "__main__":
    main()