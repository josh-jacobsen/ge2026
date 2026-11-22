"""Sanity checks on geocoded venues: flag pins that are far from the other venues of their electorate.

Suburb names repeat around New Zealand (Northcote in Auckland and Christchurch), and the geocoder only checks that
a hit is somewhere in the country, so a wrong-city hit would otherwise be paired and mapped with confidence.
Method: each general electorate has a centre (median location of its geocoded election-day venues). A venue is
flagged when it is farther from that centre than max(min_km, factor x the electorate's median venue distance), so
big rural electorates are not flagged for being big. Māori electorates cover whole regions and are skipped.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from electorates import MAORI, norm_electorate
from places import haversine_m


def home_electorates(party_votes: pd.DataFrame) -> pd.DataFrame:
    """Home general electorate of every election-day venue label, per year: election_year, voting_place_raw, electorate.

    The home electorate is the general-roll electorate whose voters cast most votes at that label. Election-day
    places only: advance venues serve voters from every electorate, so they say nothing about location.
    """
    d = party_votes[(party_votes.place_kind == "election_day") & ~party_votes.electorate.map(norm_electorate).isin(MAORI)]
    t = d.groupby(["election_year", "voting_place_raw", "electorate"], as_index=False)["votes"].sum()
    return t.sort_values("votes", ascending=False).drop_duplicates(["election_year", "voting_place_raw"])[
        ["election_year", "voting_place_raw", "electorate"]
    ]


def flag_outliers(points: pd.DataFrame, min_km: float = 30, factor: float = 3, min_points: int = 5) -> pd.DataFrame:
    """points needs: group, label, lat, lon (rows without coordinates are ignored).

    Adds centre_lat, centre_lon, distance_km, threshold_km, outlier. Groups with fewer than min_points venues are
    never flagged (the centre would be meaningless).
    """
    p = points.dropna(subset=["lat", "lon"]).copy()
    out = []
    for _, g in p.groupby("group"):
        g = g.copy()
        clat, clon = g.lat.median(), g.lon.median()
        d = haversine_m(g.lat.values, g.lon.values, clat, clon) / 1000
        g["centre_lat"], g["centre_lon"], g["distance_km"] = clat, clon, d
        g["threshold_km"] = max(min_km, factor * float(np.median(d)))
        g["outlier"] = (g.distance_km > g.threshold_km) & (len(g) >= min_points)
        out.append(g)
    cols = list(points.columns) + ["centre_lat", "centre_lon", "distance_km", "threshold_km", "outlier"]
    if not out:
        return pd.DataFrame(columns=cols)
    return pd.concat(out).sort_values("distance_km", ascending=False)[cols]
