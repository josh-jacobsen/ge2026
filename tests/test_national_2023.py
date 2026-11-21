"""2023 staging vs the Commission's independent turnout table (electorate and national totals)."""

import pandas as pd
import pytest

import etl
from electorates import MAORI, norm_electorate

OFFICIAL_PARTY_FILE = etl.RAW / "ge2023" / "_turnout" / "ge2023_party_votes_national.csv"


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


def test_national_party_votes_match_published():
    """Activates once the 2023 national party table is saved as ge2023_party_votes_national.csv
    (columns: party, party_votes), the 2023 counterpart of the 2026 national file."""
    if not OFFICIAL_PARTY_FILE.exists():
        pytest.skip(f"2023 national party table not supplied yet: {OFFICIAL_PARTY_FILE.name}")
    pub = pd.read_csv(OFFICIAL_PARTY_FILE)
    pub["party"] = pub["party"].map(etl.clean_party)
    tables = etl.build()
    d = tables["stg_party_votes"].query("election_year == 2023 and place_kind == 'total'")
    staged = d.groupby("party")["votes"].sum()
    merged = pub.set_index("party")[["party_votes"]].join(staged.rename("staged"), how="outer")
    assert (merged.party_votes == merged.staged).all(), merged[merged.party_votes != merged.staged]
