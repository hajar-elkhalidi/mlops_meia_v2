import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(
    os.getenv("DUCKDB_PATH", "morocco_housing_ingestion.duckdb")
)
DATASET_NAME = os.getenv("DLT_DATASET_NAME", "raw_immobilier")
TABLE_NAME = "housing_listings"

con = duckdb.connect(str(DB_PATH))

print(f"Database: {DB_PATH}")
print(f"Dataset: {DATASET_NAME}")

print("\nTables:")
print(con.sql("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema = ?
    ORDER BY table_name
""", params=[DATASET_NAME]))

print("\nTotal listings:")
print(con.sql(
    f"SELECT COUNT(*) AS total FROM {DATASET_NAME}.{TABLE_NAME}"
))

print("\nListings by source:")
print(con.sql(
    f"""
    SELECT source, COUNT(*) AS listings
    FROM {DATASET_NAME}.{TABLE_NAME}
    GROUP BY source
    ORDER BY source
    """
))

print("\nColumns:")
print(con.sql("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = ?
      AND table_name = ?
    ORDER BY ordinal_position
""", params=[DATASET_NAME, TABLE_NAME]))

print("\nSample:")
print(con.sql(
    f"SELECT * FROM {DATASET_NAME}.{TABLE_NAME} LIMIT 5"
))

con.close()
