"""Venue-level results and cross-election matching by distance.

A venue is listed under every electorate whose voters used it (advance venues under dozens), so results are
summed across listings to give one row per venue per election. Venues from 2023 and 2026 are then paired by
geocoded location, which survives renamed venues and the 2025 electorate boundary changes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from electorates import MAORI, norm_electorate, venue_key

ORDINARY = ("advance", "election_day")


def venue_id(place_raw: str) -> str:
    suburb, venue = venue_key(place_raw)
    return f"{suburb}|{venue}"


def venue_results(party_votes: pd.DataFrame, kinds=ORDINARY) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (votes, venues, raw_map).

    votes    election_year, venue_id, party, votes          summed over every electorate listing and both sections
    venues   election_year, venue_id, label, home_electorate, total_votes
    raw_map  election_year, venue_id, voting_place_raw      every raw label behind a venue (for joining geocodes)
    """
    d = party_votes[party_votes.place_kind.isin(kinds)].copy()
    raw_ids = {raw: venue_id(raw) for raw in d.voting_place_raw.unique()}
    d["venue_id"] = d.voting_place_raw.map(raw_ids)

    votes = d.groupby(["election_year", "venue_id", "party"], as_index=False)["votes"].sum()

    by_label = d.groupby(["election_year", "venue_id", "electorate", "voting_place_raw"], as_index=False)["votes"].sum()
    totals = by_label.groupby(["election_year", "venue_id"], as_index=False)["votes"].sum().rename(columns={"votes": "total_votes"})
    label = by_label.sort_values("votes", ascending=False).drop_duplicates(["election_year", "venue_id"])[
        ["election_year", "venue_id", "voting_place_raw"]
    ].rename(columns={"voting_place_raw": "label"})
    # home electorate: general-roll electorate with the most votes at the venue (Māori seats overlay everything)
    general = by_label[~by_label.electorate.map(norm_electorate).isin(MAORI)]
    home = (
        general.groupby(["election_year", "venue_id", "electorate"], as_index=False)["votes"].sum()
        .sort_values("votes", ascending=False).drop_duplicates(["election_year", "venue_id"])
        .rename(columns={"electorate": "home_electorate"})[["election_year", "venue_id", "home_electorate"]]
    )
    venues = totals.merge(label, on=["election_year", "venue_id"]).merge(home, on=["election_year", "venue_id"], how="left")
    raw_map = by_label[["election_year", "venue_id", "voting_place_raw"]].drop_duplicates()
    return votes, venues, raw_map


def attach_coords(venues: pd.DataFrame, raw_map: pd.DataFrame, geo: pd.DataFrame) -> pd.DataFrame:
    """Add lat/lon per (year, venue): the first geocoded raw label of that venue and year."""
    g = raw_map.merge(geo[["voting_place_raw", "lat", "lon"]].dropna(), on="voting_place_raw", how="inner")
    c = g.groupby(["election_year", "venue_id"], as_index=False)[["lat", "lon"]].first()
    return venues.merge(c, on=["election_year", "venue_id"], how="left")


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres; arguments broadcast (use [:, None] and [None, :] for a matrix)."""
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 12742000 * np.arcsin(np.sqrt(a))


def match_by_distance(a: pd.DataFrame, b: pd.DataFrame, max_m: float = 300) -> pd.DataFrame:
    """Pair rows of `a` with rows of `b` by location. Needs lat/lon columns.

    Only *mutual* nearest neighbours within max_m are paired, so each venue is used at most once and a venue
    with no real counterpart (closed, new, or moved) stays unmatched instead of grabbing a neighbour's.
    Returns a_index, b_index, dist_m (indexes refer to the labels of `a` and `b`).
    """
    a, b = a.dropna(subset=["lat", "lon"]), b.dropna(subset=["lat", "lon"])
    if a.empty or b.empty:
        return pd.DataFrame(columns=["a_index", "b_index", "dist_m"])
    d = haversine_m(a.lat.values[:, None], a.lon.values[:, None], b.lat.values[None, :], b.lon.values[None, :])
    nearest_b = d.argmin(axis=1)           # for each a, the closest b
    nearest_a = d.argmin(axis=0)           # for each b, the closest a
    ai = np.arange(len(a))
    mutual = nearest_a[nearest_b] == ai
    close = d[ai, nearest_b] <= max_m
    keep = mutual & close
    return pd.DataFrame({"a_index": a.index[ai[keep]], "b_index": b.index[nearest_b[keep]], "dist_m": d[ai[keep], nearest_b[keep]]})
