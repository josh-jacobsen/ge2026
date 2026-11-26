"""One row per voting venue and election, for ranking booths by Green or TOP vote.

A venue is the physical place: its votes are summed over every electorate that lists it (as in notebook 04's
swing map), and it belongs to its *home electorate*, the general-roll electorate with the most votes there
(`places.venue_results`). `home_*` columns count only votes from voters of that home electorate, so the share of
a venue's vote that is local is visible (a mall near an electorate edge, or a CBD hall, is mostly not local).
"""

from __future__ import annotations

import pandas as pd

from places import ORDINARY, venue_id, venue_results

GREEN, TOP = "Green Party", "The Opportunities Party (TOP)"
PARTIES = {"green": GREEN, "top": TOP}


def venue_table(pv: pd.DataFrame, parties: dict[str, str] = PARTIES) -> pd.DataFrame:
    """Columns: election_year, venue_id, place, suburb, venue, home_electorate, n_electorates, total, home_total,
    then for each key in `parties`: <key> and <key>_home (party votes, all voters / home-electorate voters)."""
    votes, venues, _ = venue_results(pv)
    venues = venues.dropna(subset=["home_electorate"])
    d = pv[pv.place_kind.isin(ORDINARY)].copy()
    ids = {raw: venue_id(raw) for raw in d.voting_place_raw.unique()}
    d["venue_id"] = d.voting_place_raw.map(ids)
    d = d.merge(venues[["election_year", "venue_id", "home_electorate"]], on=["election_year", "venue_id"])
    home = d[d.electorate == d.home_electorate]
    key = ["election_year", "venue_id"]

    out = venues.rename(columns={"label": "place", "total_votes": "total"})[key + ["place", "home_electorate", "total"]]
    out = out.merge(d.groupby(key).electorate.nunique().rename("n_electorates").reset_index(), on=key)
    out = out.merge(home.groupby(key).votes.sum().rename("home_total").reset_index(), on=key, how="left")
    for name, party in parties.items():
        allv = votes[votes.party == party].groupby(key).votes.sum().rename(name).reset_index()
        hv = home[home.party == party].groupby(key).votes.sum().rename(f"{name}_home").reset_index()
        out = out.merge(allv, on=key, how="left").merge(hv, on=key, how="left")
    num = [c for c in out.columns if c not in ("election_year", "venue_id", "place", "home_electorate")]
    out[num] = out[num].fillna(0).astype(int)
    parts = out.place.str.split(",", n=1)
    out["suburb"] = parts.str[0].str.strip()
    out["venue"] = parts.str[1].fillna("").str.strip()
    return out


def top_n(vt: pd.DataFrame, party: str, by: str, min_votes: int = 0, n: int = 3) -> pd.DataFrame:
    """Top `n` venues per (year, home electorate) for `party` ('green'/'top'), by "votes" or "pct" of all venue ballots."""
    d = vt[vt.total >= min_votes].copy() if min_votes else vt.copy()
    d["pct"] = 100 * d[party] / d.total.where(d.total > 0)
    d["home_pct"] = 100 * d[f"{party}_home"] / d[party].where(d[party] > 0)
    col = party if by == "votes" else "pct"
    d = d[d[party] > 0].sort_values(["election_year", "home_electorate", col, "total"], ascending=[True, True, False, False])
    d = d.groupby(["election_year", "home_electorate"]).head(n).copy()
    d["rank"] = d.groupby(["election_year", "home_electorate"]).cumcount() + 1
    return d
