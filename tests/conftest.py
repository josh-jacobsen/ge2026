"""Shared fixtures. `tables` rebuilds the staging tables from data/raw (a few seconds, once per session)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import etl  # noqa: E402


@pytest.fixture(scope="session")
def tables():
    if not (etl.RAW / "ge2023").exists() or not (etl.RAW / "ge2026").exists():
        pytest.skip("raw data not present")
    return etl.build()


@pytest.fixture(scope="session")
def party_votes(tables):
    return tables["stg_party_votes"]


@pytest.fixture(scope="session")
def official_2026():
    return json.loads((ROOT / "tests" / "data" / "official_2026_national_summary.json").read_text())


@pytest.fixture(scope="session")
def official_2023():
    return json.loads((ROOT / "tests" / "data" / "official_2023_national_summary.json").read_text())
