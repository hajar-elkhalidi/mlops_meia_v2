import csv
from pathlib import Path

DATA = Path("data/housing_data.csv")

def test_dataset_shape():
    with DATA.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4675
    assert set(["new_price","surface","City","Type"]).issubset(rows[0])

def test_listing_ids_are_unique():
    with DATA.open(encoding="utf-8-sig", newline="") as f:
        ids = [r["Unnamed: 0"] for r in csv.DictReader(f)]
    assert len(ids) == len(set(ids))
