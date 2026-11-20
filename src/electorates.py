"""Reconcile 2023 and 2026 electorates (2025 boundary review: 72 -> 71 electorates).

Evidence-based crosswalk: the same venue used on election day in a 2023 electorate and a 2026
electorate means the two seats overlap there. Election-day places only: advance venues serve voters
from every electorate, so they say nothing about geography.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging"
REFERENCE = ROOT / "data" / "reference"


# The seven Māori electorates overlay the general ones (same venues), so they are reconciled separately.
MAORI = {"hauraki waikato", "ikaroa rawhiti", "tamaki makaurau", "te tai hauauru", "te tai tokerau", "te tai tonga", "waiariki"}


def norm_electorate(name: str) -> str:
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace("-", " ").strip()


def venue_key(place_raw: str) -> tuple[str, str]:
    """(suburb, venue) normalised so '575 Albany Highway' and '575a Albany Highway' compare equal."""
    parts = [p.strip() for p in place_raw.split(",")]
    suburb, rest = parts[0], " ".join(parts[1:])
    text = unicodedata.normalize("NFKD", f"{rest}").encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\b(\d+)[a-z]\b", r"\1", text)  # 575a -> 575
    text = re.sub(r"\b(road|rd)\b", "road", text)
    text = re.sub(r"\b(street|st)\b", "street", text)
    text = re.sub(r"\b(avenue|ave)\b", "avenue", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return norm_electorate(suburb), " ".join(text.split())


def place_totals(party_votes: pd.DataFrame, kinds=("election_day",)) -> pd.DataFrame:
    """One row per (year, roll, venue): its *home* electorate, the electorate whose voters cast most votes there.

    A venue is listed under every electorate whose voters used it (its own seat, the overlapping Māori
    seat, neighbouring seats), so pairing every listing across years would invent overlaps.
    `votes` is the home electorate's vote at the venue; `venue_total` is all electorates combined.
    """
    d = party_votes[party_votes.place_kind.isin(kinds)]
    t = d.groupby(["election_year", "electorate", "voting_place_raw"], as_index=False)["votes"].sum()
    keys = t["voting_place_raw"].map(venue_key)
    t["suburb_key"], t["venue_key"] = keys.str[0], keys.str[1]
    t["maori"] = t.electorate.map(norm_electorate).isin(MAORI)
    # two raw labels can normalise to the same venue within one electorate: add them up
    t = t.groupby(["election_year", "maori", "suburb_key", "venue_key", "electorate"], as_index=False).agg(
        votes=("votes", "sum"), voting_place_raw=("voting_place_raw", "first")
    )
    t["venue_total"] = t.groupby(["election_year", "maori", "suburb_key", "venue_key"]).votes.transform("sum")
    t["home_share"] = t.votes / t.venue_total
    home = t.sort_values("votes", ascending=False).drop_duplicates(["election_year", "maori", "suburb_key", "venue_key"])
    return home.reset_index(drop=True)


def match_places(t: pd.DataFrame, fuzzy_cutoff: float = 0.9) -> pd.DataFrame:
    """General and Māori electorates are matched independently, then stacked."""
    out = [_match(t[t.maori == flag], fuzzy_cutoff).assign(roll="maori" if flag else "general") for flag in (False, True)]
    return pd.concat(out, ignore_index=True)


def _match(t: pd.DataFrame, fuzzy_cutoff: float) -> pd.DataFrame:
    """Pair each 2026 place with a 2023 place: exact normalised key first, then fuzzy within suburb."""
    a = t[t.election_year == 2023].rename(columns=lambda c: c + "_2023" if c not in () else c)
    b = t[t.election_year == 2026].rename(columns=lambda c: c + "_2026" if c not in () else c)
    exact = b.merge(a, left_on=["suburb_key_2026", "venue_key_2026"], right_on=["suburb_key_2023", "venue_key_2023"], how="left")
    exact["match"] = exact["voting_place_raw_2023"].notna().map({True: "exact", False: ""})

    # fuzzy pass for the rest, same suburb only
    unmatched = exact[exact.match == ""].index
    pool = a.groupby("suburb_key_2023")
    for i in unmatched:
        r = exact.loc[i]
        if r.suburb_key_2026 not in pool.groups:
            continue
        cand = pool.get_group(r.suburb_key_2026)
        scores = cand.venue_key_2023.map(lambda v: difflib.SequenceMatcher(None, r.venue_key_2026, v).ratio())
        j = scores.idxmax()
        if scores[j] >= fuzzy_cutoff:
            for col in a.columns:
                exact.at[i, col] = cand.loc[j, col]
            exact.at[i, "match"] = f"fuzzy {scores[j]:.2f}"
    exact.loc[exact.match == "", "match"] = "none"
    return exact


def crosswalk(matched: pd.DataFrame) -> pd.DataFrame:
    """Votes at matched election-day places by (2026 electorate, 2023 electorate), with shares of each side."""
    m = matched[matched.match != "none"]
    x = m.groupby(["roll", "electorate_2026", "electorate_2023"], as_index=False).agg(
        votes_2026=("votes_2026", "sum"), votes_2023=("votes_2023", "sum"), places=("voting_place_raw_2026", "count")
    )
    x["share_of_2026"] = x.votes_2026 / x.groupby("electorate_2026").votes_2026.transform("sum") * 100
    x["share_of_2023"] = x.votes_2023 / x.groupby("electorate_2023").votes_2023.transform("sum") * 100
    return x.sort_values(["roll", "electorate_2026", "share_of_2026"], ascending=[True, True, False])


def summarise_2026(x: pd.DataFrame, matched: pd.DataFrame, min_share: float = 20.0) -> pd.DataFrame:
    """One row per 2026 electorate: where its (matched) election-day votes came from, and a relationship label."""
    rows = []
    cov = matched.assign(ok=matched.match != "none").groupby("electorate_2026").apply(
        lambda d: (d.votes_2026 * d.ok).sum() / d.votes_2026.sum() * 100
    )
    for e26, d in x.groupby("electorate_2026"):
        d = d.sort_values("share_of_2026", ascending=False)
        same = d[d.electorate_2023.map(norm_electorate) == norm_electorate(e26)]
        same_share = float(same.share_of_2026.iloc[0]) if len(same) else 0.0
        big = d[d.share_of_2026 >= min_share]
        top = d.iloc[0]
        if same_share >= 80:
            rel = "continuing"
        elif same_share >= 50:
            rel = "continuing, boundaries changed"
        elif len(big) >= 2:
            rel = "merged/redrawn from " + " + ".join(big.electorate_2023)
        elif top.share_of_2026 >= 60:
            rel = f"successor of {top.electorate_2023}"
        else:
            rel = "mixed"
        rows.append({
            "roll": d.roll.iloc[0], "electorate_2026": e26, "relationship": rel,
            "primary_2023": top.electorate_2023, "primary_share": round(top.share_of_2026, 1),
            "same_name_share": round(same_share, 1),
            "sources": "; ".join(f"{r.electorate_2023} {r.share_of_2026:.0f}%" for r in big.itertuples()),
            "matched_vote_coverage": round(float(cov.get(e26, 0)), 1),
        })
    return pd.DataFrame(rows).sort_values(["roll", "electorate_2026"]).reset_index(drop=True)


def summarise_2023(x: pd.DataFrame, min_share: float = 20.0) -> pd.DataFrame:
    """One row per 2023 electorate: where its (matched) votes ended up in 2026."""
    rows = []
    for e23, d in x.groupby("electorate_2023"):
        d = d.sort_values("share_of_2023", ascending=False)
        same = d[d.electorate_2026.map(norm_electorate) == norm_electorate(e23)]
        same_share = float(same.share_of_2023.iloc[0]) if len(same) else 0.0
        big = d[d.share_of_2023 >= min_share]
        if same_share >= 80:
            rel = "continues"
        elif same_share >= 50:
            rel = "continues, boundaries changed"
        elif len(same) == 0 and len(big) >= 2:
            rel = "split/abolished into " + " + ".join(big.electorate_2026)
        elif len(same) == 0:
            rel = f"renamed to {d.iloc[0].electorate_2026}"
        else:
            rel = "split: " + " + ".join(big.electorate_2026)
        rows.append({"roll": d.roll.iloc[0], "electorate_2023": e23, "relationship": rel, "same_name_share": round(same_share, 1),
                     "destinations": "; ".join(f"{r.electorate_2026} {r.share_of_2023:.0f}%" for r in big.itertuples())})
    return pd.DataFrame(rows).sort_values(["roll", "electorate_2023"]).reset_index(drop=True)
