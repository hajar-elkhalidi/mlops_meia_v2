import os
from pathlib import Path
import duckdb
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("DUCKDB_PATH", "morocco_housing.duckdb"))
DATASET_NAME = os.getenv("DLT_DATASET_NAME", "raw_immobilier")

con = duckdb.connect(str(DB_PATH))
tables = con.sql("SHOW TABLES").fetchall()
print("Tables:", tables)

for (table,) in tables:
    print(f"\n--- {table} ---")
    print(con.sql(f'SELECT COUNT(*) AS rows FROM "{table}"').df())
    print(con.sql(f'SELECT * FROM "{table}" LIMIT 5').df())

con.close()
