"""2023 staging vs the Commission's independent turnout table (electorate and national totals)."""

import pandas as pd
import pytest

import etl
from electorates import MAORI, norm_electorate

OFFICIAL_PARTY_FILE = etl.NATIONAL_2023


def test_electorate_counts(party_votes, official_2023):
    names = party_votes[party_votes.election_year == 2023].electorate.unique()
    maori = [n for n in names if norm_electorate(n) in MAORI]
    assert len(names) == official_2023["electorates"]
    assert len(maori) == official_2023["maori_electorates"]
    assert len(names) - len(maori) == official_2023["general_electorates"]


def test_national_total_and_rolls(party_votes, official_2023):
    d = party_votes[(party_votes.election_year == 2023) & (party_votes.place_kind == "total")]
    is_maori = d.electorate.map(norm_electorate).isin(MAORI)
    assert d.votes.sum() == official_2023["total_party_votes"]
    assert d[~is_maori].votes.sum() == official_2023["general_party_votes"]
    assert d[is_maori].votes.sum() == official_2023["maori_party_votes"]


def test_official_national_figures_match_the_turnout_file(official_2023):
    _, totals = etl.load_turnout_2023()
    assert totals["combined"] == official_2023["total_party_votes"]
    assert totals["general"] == official_2023["general_party_votes"]
    assert totals["maori"] == official_2023["maori_party_votes"]


def test_each_electorate_total_matches_turnout_table(tables):
    chk = etl.checks_turnout_2023(tables)
    assert not chk[["valid_total", "staging_total"]].isna().any().any(), "electorate on only one side"
    assert (chk["diff"] == 0).all(), chk[chk["diff"] != 0]


def test_every_electorate_reconciles_to_its_total_row(tables):
    chk = etl.checks(tables)
    assert (chk[chk.election_year == 2023]["diff"] == 0).all()


PUBLISHED = pd.read_csv(OFFICIAL_PARTY_FILE)
PUBLISHED["party"] = PUBLISHED["party"].map(etl.clean_party)


@pytest.fixture(scope="module")
def staged_2023(party_votes):
    d = party_votes[(party_votes.election_year == 2023) & (party_votes.place_kind == "total")]
    return d.groupby("party")["votes"].sum()


@pytest.mark.parametrize("row", list(PUBLISHED.itertuples()), ids=lambda r: r.party)
def test_party_votes_match_published(row, staged_2023):
    assert staged_2023.get(row.party) == row.party_votes


def test_no_party_missing_from_published_table(staged_2023):
    assert set(staged_2023.index) == set(PUBLISHED.party)


def test_published_table_total(staged_2023, official_2023):
    assert PUBLISHED.party_votes.sum() == official_2023["total_party_votes"]
    assert staged_2023.sum() == official_2023["total_party_votes"]


def test_published_percentages_consistent_with_votes():
    # The Commission's percentages are slightly truncated, never more than 0.01 below the exact value.
    exact = PUBLISHED.party_votes / PUBLISHED.party_votes.sum() * 100
    assert ((exact - PUBLISHED.pct_votes).between(-0.0001, 0.0101)).all()


def test_published_seats_add_up(official_2023):
    p = PUBLISHED.fillna(0)
    assert (p.electorate_seats + p.list_seats == p.total_seats).all()
    assert p.electorate_seats.sum() == official_2023["electorate_seats"]
    assert p.list_seats.sum() == official_2023["list_seats"]
    assert p.total_seats.sum() == official_2023["total_seats"]


def test_port_waikato_has_party_votes_but_no_candidate_votes(tables, official_2023):
    """72 electorates voted for parties, but only 71 electorate seats were decided (Port Waikato's candidate vote
    was held separately), so it has no candidate-vote file. This is expected, not a missing download."""
    party = set(tables["stg_party_votes"].query("election_year == 2023").electorate)
    cand = set(tables["stg_candidate_votes"].query("election_year == 2023").electorate)
    assert len(cand) == official_2023["electorates_with_candidate_votes"] == official_2023["electorate_seats"]
    assert party - cand == set(official_2023["party_only_electorates"])
