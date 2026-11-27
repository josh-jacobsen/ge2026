"""data/raw/ge2026_final/out.csv (final count, special votes included) vs the Commission's final national results.

The national table (`ge2026_party_votes_national_final.csv`) is the official overall result copied from the Commission's
results page; out.csv is the per-electorate file. They are independent, so agreement is a real check on out.csv.
"""

import pandas as pd
import pytest

import etl
from electorates import MAORI, norm_electorate

OUT = etl.RAW / "ge2026_final" / "out.csv"
NATIONAL_TOTAL_PARTY_VOTES = 2_888_890  # "Total" row of the official table
ELECTORATES = 71
MAJOR = ["National Party", "Labour Party", "Green Party", "ACT New Zealand", "New Zealand First Party", "Opportunity Party", "Te Pāti Māori"]

pytestmark = pytest.mark.skipif(not OUT.exists(), reason="data/raw/ge2026_final/out.csv not present")


@pytest.fixture(scope="module")
def out():
    d = pd.read_csv(OUT, dtype={"id": str, "electorate": str, "type": str, "name": str})
    d["name"] = d.name.where(d.type != "party", d.name.map(etl.clean_party))
    return d


@pytest.fixture(scope="module")
def national():
    n = pd.read_csv(etl.NATIONAL_2026_FINAL)
    n["party"] = n.party.map(etl.clean_party)
    return n.set_index("party")


@pytest.fixture(scope="module")
def party(out):
    return out[out.type == "party"]


@pytest.fixture(scope="module")
def cand(out):
    return out[out.type == "candidate"]


# --- shape of the file ---------------------------------------------------------------------------------------------

def test_columns_types_and_no_missing(out):
    assert list(out.columns) == ["id", "electorate", "type", "name", "votes"]
    assert not out.isna().any().any()
    assert set(out.type) == {"party", "candidate"}
    assert pd.api.types.is_integer_dtype(out.votes) and (out.votes >= 0).all()


def test_no_duplicate_rows(out):
    assert not out.duplicated(["electorate", "type", "name"]).any()


def test_71_electorates_with_one_id_each(out):
    assert out.electorate.nunique() == out.id.nunique() == ELECTORATES
    assert out.groupby("electorate").id.nunique().eq(1).all()
    assert sorted(out.id.unique()) == [f"{i:02d}" for i in range(1, ELECTORATES + 1)]


def test_seven_maori_electorates(out):
    assert sum(norm_electorate(e) in MAORI for e in out.electorate.unique()) == 7


def test_same_electorates_as_preliminary_staging(out, party_votes):
    prelim = set(party_votes[party_votes.election_year == 2026].electorate)
    assert set(out.electorate) == prelim


# --- party vote vs the official national table ----------------------------------------------------------------------

def test_every_electorate_lists_every_party(party, national):
    parties = party.groupby("electorate").name.apply(frozenset)
    assert (parties == frozenset(national.index)).all()


def test_party_totals_match_national_table(party, national):
    got = party.groupby("name").votes.sum()
    assert set(got.index) == set(national.index)
    diff = (got - national.party_votes).dropna()
    assert (diff == 0).all(), diff[diff != 0].to_dict()


def test_total_party_votes(party, national):
    assert party.votes.sum() == national.party_votes.sum() == NATIONAL_TOTAL_PARTY_VOTES


def test_party_shares_match_published_percentages(party, national):
    # the Commission's percentages are truncated (or rounded) to 2 decimals
    share = party.groupby("name").votes.sum() / party.votes.sum() * 100
    assert ((share - national.pct_votes).abs() < 0.0101).all()


# --- candidate vote ------------------------------------------------------------------------------------------------

def test_candidate_votes_close_to_party_votes_in_every_electorate(party, cand):
    # fewer valid candidate votes than party votes (informal candidate votes), but never by much
    ratio = cand.groupby("electorate").votes.sum() / party.groupby("electorate").votes.sum()
    assert ratio.between(0.90, 1.0).all(), ratio[~ratio.between(0.90, 1.0)].to_dict()


def test_electorate_seat_winners_match_official_seats(cand, national):
    # out.csv has no candidate party. Winners known from data/reference/ge2026_winner_parties.csv are counted by party;
    # the rest must fit exactly into the seats the official table still has to give.
    winners = cand.loc[cand.groupby("electorate").votes.idxmax()]
    assert len(winners) == ELECTORATES
    assert winners.groupby("electorate").size().eq(1).all()
    known = pd.read_csv(etl.ROOT / "data" / "reference" / "ge2026_winner_parties.csv").set_index("candidate").party
    parties = winners.name.map(known)
    official = national.electorate_seats.dropna().astype(int)
    left = official.sub(parties.value_counts(), fill_value=0)
    assert (left >= 0).all(), f"more known winners than official seats: {left[left < 0].to_dict()}"
    assert left.sum() == parties.isna().sum(), "seats left to assign must equal winners with no known party"
    assert official.sum() == ELECTORATES


# --- consistency with the preliminary count -------------------------------------------------------------------------

@pytest.fixture(scope="module")
def prelim(party_votes):
    d = party_votes[(party_votes.election_year == 2026) & (party_votes.count_stage == "preliminary") & (party_votes.place_kind == "total")]
    return d.groupby(["electorate", "party"]).votes.sum()


def test_final_electorate_totals_exceed_preliminary(party, prelim):
    # the final count adds special/overseas votes (about +11% to +39% per electorate), it does not remove votes
    f = party.groupby("electorate").votes.sum()
    ratio = f / prelim.groupby("electorate").sum()
    assert ratio.between(1.0, 1.6).all(), ratio[~ratio.between(1.0, 1.6)].to_dict()


def _change(name, party, prelim):
    f = party[party.name == etl.clean_party(name)].set_index("electorate").votes
    return f - prelim.xs(etl.clean_party(name), level="party")


@pytest.mark.parametrize("name", [m for m in MAJOR if m != "Te Pāti Māori"])
def test_major_party_never_falls_in_an_electorate(name, party, prelim):
    # Some minor parties lost votes between counts (preliminary figures corrected); the parties with seats must not.
    d = _change(name, party, prelim)
    assert (d >= 0).all(), d[d < 0].to_dict()


def test_te_pati_maori_falls_only_where_known(party, prelim):
    # One unexplained drop: Hutt South 113 (preliminary) -> 76 (final). The national total still matches the official
    # table, so out.csv is consistent; the preliminary Hutt South figure was probably wrong. Review if this ever changes.
    d = _change("Te Pāti Māori", party, prelim)
    assert d[d < 0].to_dict() == {"Hutt South": -37}
