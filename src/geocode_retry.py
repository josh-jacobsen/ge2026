"""Second geocoding pass for voting places the first pass (geocode.py) could not find.

Only rows with no coordinates in the cache are retried. Each place gets cleaner queries (parenthetical notes
removed, "corner A & B" reduced to one street, venue name alone, street name alone), and a hit is accepted only
if it lands within MAX_KM of other pinned venues in one of the same electorates, which rejects wrong-city hits.
Only public venue names and addresses are sent; same Nominatim limits and generic User-Agent as geocode.py.

Usage:  uv run python src/geocode_retry.py
"""

from __future__ import annotations

import re
import time

import numpy as np
import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from geocode import CACHE, STAGING, USER_AGENT, ok

MAX_KM = 40.0
NOT_A_VENUE = re.compile(r"pop[- ]?up|mobile team|taken in|care home|voting service|hospital team", re.I)


def km(lat1, lon1, lat2, lon2):
    return 111.0 * np.hypot(lat1 - lat2, (lon1 - lon2) * np.cos(np.radians(lat1)))


def clean(text: str) -> str:
    text = re.sub(r"\([^)]*\)?", " ", text)  # "(corner A & B)" and unclosed "(near ..."
    return " ".join(text.replace("  ", " ").split()).strip(" ,")


def retry_queries(place: str) -> list[str]:
    parts = [p.strip() for p in place.split(",")]
    suburb, rest = parts[0], parts[1:]
    venue = clean(rest[0]) if rest else ""
    addr_parts = [clean(p) for p in rest[1:] if not re.match(r"^(unit|shop|level|room|gate)\b", p, re.I)]
    addr_parts = [p for p in addr_parts if p]
    qs = []
    for a in addr_parts:
        a = re.sub(r"^(corner|cnr)\s+", "", a, flags=re.I)
        street = re.split(r"\s+(?:&|and)\s+", a)[0]
        qs += [f"{street}, {suburb}, New Zealand"]
    # a range like 395-427 Botanical Road -> first number only
    qs = [re.sub(r"\b(\d+)-\d+\b", r"\1", q) for q in qs]
    if venue:
        qs += [f"{venue}, {suburb}, New Zealand", f"{venue}, New Zealand"]
    seen = []
    for q in qs:
        if q not in seen:
            seen.append(q)
    return seen


def main() -> None:
    cache = pd.read_csv(CACHE)
    places = pd.read_parquet(STAGING / "stg_party_votes.parquet", columns=["voting_place_raw", "electorate", "place_kind"])
    places = places[places.place_kind.isin(["advance", "election_day"])].drop_duplicates(["voting_place_raw", "electorate"])
    pinned = places.merge(cache.dropna(subset=["lat"])[["voting_place_raw", "lat", "lon"]], on="voting_place_raw")
    by_elec = {e: g[["lat", "lon"]].to_numpy() for e, g in pinned.groupby("electorate")}
    elecs = places.groupby("voting_place_raw").electorate.agg(list)

    def plausible(place: str, lat: float, lon: float) -> bool:
        pts = [by_elec[e] for e in elecs.get(place, []) if e in by_elec]
        if not pts:
            return True
        return any(km(lat, lon, p[:, 0], p[:, 1]).min() <= MAX_KM for p in pts)

    todo = cache[cache.lat.isna() & ~cache.voting_place_raw.str.contains(NOT_A_VENUE)].voting_place_raw.tolist()
    print(f"{len(todo)} venues to retry", flush=True)
    geocode = RateLimiter(Nominatim(user_agent=USER_AGENT, timeout=15).geocode, min_delay_seconds=1.1,
                          max_retries=2, error_wait_seconds=5, swallow_exceptions=True)
    found = rejected = 0
    for n, place in enumerate(todo, 1):
        for q in retry_queries(place):
            loc = geocode(q, country_codes="nz")
            if not ok(loc):
                continue
            if plausible(place, loc.latitude, loc.longitude):
                m = cache.voting_place_raw == place
                cache.loc[m, ["lat", "lon", "matched_query", "display_name"]] = [loc.latitude, loc.longitude, f"retry: {q}", loc.address]
                found += 1
                break
            rejected += 1
        if n % 20 == 0 or n == len(todo):
            cache.to_csv(CACHE, index=False)
            print(f"  {n}/{len(todo)}  found {found}  implausible hits rejected {rejected}", flush=True)
    cache.to_csv(CACHE, index=False)
    print(f"done: {cache.lat.notna().sum()}/{len(cache)} pinned")


if __name__ == "__main__":
    main()
