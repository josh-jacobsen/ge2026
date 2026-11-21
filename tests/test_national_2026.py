"""2026 staging vs the Commission's published national results (preliminary)."""

import math

import pandas as pd
import pytest

import etl
from electorates import MAORI, norm_electorate

PUBLISHED = pd.read_csv(etl.NATIONAL_2026)
PUBLISHED["party"] = PUBLISHED["party"].map(etl.clean_party)


@pytest.fixture(scope="module")
def staged_2026(party_votes):
    d = party_votes[(party_votes.election_year == 2026) & (party_votes.place_kind == "total")]
    return d.groupby("party")["votes"].sum()


@pytest.mark.parametrize("row", list(PUBLISHED.itertuples()), ids=lambda r: r.party)
def test_party_votes_match_published(row, staged_2026):
    assert staged_2026.get(row.party) == row.party_votes


def test_no_party_missing_from_published_table(staged_2026):
    assert set(staged_2026.index) == set(PUBLISHED.party)


def test_total_party_votes(staged_2026, official_2026):
    assert PUBLISHED.party_votes.sum() == official_2026["total_party_votes"]
    assert staged_2026.sum() == official_2026["total_party_votes"]


def test_published_percentages_consistent_with_votes():
    # The Commission's percentages are slightly truncated, never more than 0.01 below the exact value.
    exact = PUBLISHED.party_votes / PUBLISHED.party_votes.sum() * 100
    assert ((exact - PUBLISHED.pct_votes).between(-0.0001, 0.0101)).all()


def test_published_seats_add_up(official_2026):
    p = PUBLISHED.fillna(0)
    assert (p.electorate_seats + p.list_seats == p.total_seats).all()
    assert p.electorate_seats.sum() == official_2026["electorate_seats"]
    assert p.list_seats.sum() == official_2026["list_seats"]
    assert p.total_seats.sum() == official_2026["total_seats"]


def test_number_of_electorates(party_votes, official_2026):
    names = party_votes[party_votes.election_year == 2026].electorate.unique()
    assert len(names) == official_2026["electorates"]
    assert sum(norm_electorate(n) in MAORI for n in names) == official_2026["maori_electorates"]
    assert official_2026["electorates"] == official_2026["electorate_seats"]  # one seat per electorate


def test_every_electorate_reconciles_to_its_total_row(tables):
    chk = etl.checks(tables)
    assert (chk[chk.election_year == 2026]["diff"] == 0).all()
