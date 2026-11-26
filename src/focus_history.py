"""Seat-level results for the focus electorates across four elections (2017, 2020, 2023, 2026), and political blocs.

2017 and 2020 are seat totals typed in from the Commission's results pages (data/reference/focus_seats_history.csv);
2023 and 2026 come from the staged files. 2023 uses all votes (special included) so it matches the final 2017/2020 figures;
2026 follows the vote scope and count stage given.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import vote_scope

ROOT = Path(__file__).resolve().parents[1]
YEARS = [2017, 2020, 2023, 2026]

# One name per party lineage (re-registered or renamed between elections).
CANON = {
    "Conservative": "Conservative", "New Conservative": "Conservative", "New Conservatives": "Conservative",
    "Māori Party": "Te Pāti Māori", "Te Pāti Māori": "Te Pāti Māori",
    "NZ Outdoors Party": "NZ Outdoors", "NZ Outdoors & Freedom Party": "NZ Outdoors",
    "Social Credit": "Social Credit", "Democrats for Social Credit": "Social Credit",
}


def canon(party: str) -> str:
    return CANON.get(party, party)


def load_seat_table(seats, vote_scope_: str = "ordinary", count_stage: str = "preliminary", root: Path = ROOT):
    """One row per seat × year × vote type × party (canonical names). Returns (table, basis label for 2026)."""
    st = root / "data/staging"
    hist = pd.read_csv(root / "data/reference/focus_seats_history.csv")
    hist = hist[hist.electorate.isin(seats)]
    rows = [hist.rename(columns={"party": "party_raw"})[["election_year", "electorate", "vote_type", "party_raw", "votes"]]]

    p = pd.read_parquet(st / "stg_party_votes.parquet")
    p23 = p[(p.election_year == 2023) & (p.place_kind != "total") & p.electorate.isin(seats)]
    rows.append(p23.groupby(["election_year", "electorate", "party"], as_index=False).votes.sum()
                .rename(columns={"party": "party_raw"}).assign(vote_type="party"))
    c23 = pd.read_parquet(st / "stg_candidate_party.parquet")
    c23 = c23[c23.electorate.isin(seats)]
    rows.append(c23.rename(columns={"party": "party_raw"})[["election_year", "electorate", "party_raw", "votes"]].assign(vote_type="candidate"))

    p26 = vote_scope.load("stg_party_votes", vote_scope_, count_stage, staging=st)
    p26 = p26[(p26.election_year == 2026) & p26.electorate.isin(seats)]
    rows.append(p26.groupby(["election_year", "electorate", "party"], as_index=False).votes.sum()
                .rename(columns={"party": "party_raw"}).assign(vote_type="party"))
    k26 = vote_scope.load("stg_candidate_votes", vote_scope_, count_stage, staging=st)
    k26 = k26[(k26.election_year == 2026) & k26.electorate.isin(seats)].groupby(["election_year", "electorate", "candidate"], as_index=False).votes.sum()
    k26 = k26.merge(pd.read_csv(root / "data/reference/ge2026_focus_candidates.csv"), on=["electorate", "candidate"], how="left")
    if k26.party.isna().any():
        raise ValueError(f"no party for 2026 candidates: {k26[k26.party.isna()].candidate.tolist()}")
    rows.append(k26.rename(columns={"party": "party_raw"})[["election_year", "electorate", "party_raw", "votes"]].assign(vote_type="candidate"))

    seat = pd.concat(rows, ignore_index=True)
    seat["party"] = seat.party_raw.map(canon)
    seat = seat.groupby(["election_year", "electorate", "vote_type", "party"], as_index=False).votes.sum()
    totals = seat.groupby(["election_year", "electorate", "vote_type"]).votes.sum().unstack()
    if len(totals) != len(list(seats)) * len(YEARS) or totals.isna().any().any():
        raise ValueError(f"a seat-year is missing a vote type:\n{totals}")
    return seat, f"{count_stage}, {vote_scope_} votes"


BLOCS = {
    "Left": ["Labour Party", "Green Party", "The Opportunities Party (TOP)"],
    "Right": ["National Party", "ACT New Zealand", "New Zealand First Party"],
}


def bloc_shares(seat: pd.DataFrame, vote_type: str, blocs: dict[str, list[str]] = BLOCS) -> pd.DataFrame:
    """Per seat × year: each bloc's % of ALL valid votes of that type, `Other` (everyone else), and the bloc shares
    as a % of the two blocs together (`<bloc> of two-bloc`, which ignores minor-party noise between elections)."""
    d = seat[seat.vote_type == vote_type]
    total = d.groupby(["electorate", "election_year"]).votes.sum()
    out = pd.DataFrame(index=total.index)
    for name, parties in blocs.items():
        out[name] = d[d.party.isin(parties)].groupby(["electorate", "election_year"]).votes.sum().reindex(total.index).fillna(0) / total * 100
    out["Other"] = 100 - sum(out[n] for n in blocs)
    two = sum(out[n] for n in blocs)
    for name in blocs:
        out[f"{name} of two-bloc"] = out[name] / two * 100
    first, second = list(blocs)
    out[f"lead ({first} - {second})"] = out[first] - out[second]
    return out
