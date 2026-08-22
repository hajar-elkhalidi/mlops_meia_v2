import csv
from pathlib import Path


def test_morocco_file_exists():
    assert Path("data/housing_data.csv").exists()


def test_casa_file_exists():
    assert Path("data/casa_housing.csv").exists()


def test_morocco_has_no_description_requirement():
    with open("data/housing_data.csv", encoding="utf-8-sig", newline="") as f:
        headers = csv.DictReader(f).fieldnames
    assert headers is not None


def test_casa_headers():
    with open("data/casa_housing.csv", encoding="utf-8-sig", newline="") as f:
        headers = csv.DictReader(f).fieldnames
    assert {"Type", "Localisation", "Price", "Area", "Price_m2"} <= set(headers)
