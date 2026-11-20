"""Geocode voting places with Nominatim (OpenStreetMap), caching results on disk.

Only public voting-place names/addresses are sent. Nominatim policy: max 1 request/sec and an
identifying User-Agent, so this is slow-ish on the first run and instant afterwards.

Usage:  uv run python src/geocode.py
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging"
CACHE = ROOT / "data" / "geo" / "geocode_cache.csv"
USER_AGENT = "nz-election-analysis-notebook"

# Rough bounding box around mainland NZ (plus Chatham-free margin), used to reject bad hits.
LAT_RANGE, LON_RANGE = (-47.5, -34.0), (166.0, 179.0)


def extract_address(place: str) -> str:
    """Last comma-separated chunk(s) that look like a street address, else ''."""
    parts = [p.strip() for p in place.split(",")]
    for i, p in enumerate(parts[1:], start=1):
        if re.match(r"^(\d|unit|shop|level|corner|cnr)", p, re.I):
            # keep from the first address-ish chunk to the end, dropping unit/level noise
            tail = [q for q in parts[i:] if not re.match(r"^(unit|shop|level|room)\b", q, re.I)]
            return ", ".join(tail) or p
    return ""


def queries_for(place: str) -> list[str]:
    parts = [p.strip() for p in place.split(",")]
    suburb = parts[0]
    venue = parts[1] if len(parts) > 1 else ""
    addr = extract_address(place)
    qs = []
    if addr:
        qs.append(f"{addr}, {suburb}, New Zealand")
    if venue:
        qs.append(f"{venue}, {suburb}, New Zealand")
    return qs


def ok(loc) -> bool:
    return loc is not None and LAT_RANGE[0] <= loc.latitude <= LAT_RANGE[1] and LON_RANGE[0] <= loc.longitude <= LON_RANGE[1]


def load_cache() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_csv(CACHE)
    return pd.DataFrame(columns=["voting_place_raw", "lat", "lon", "matched_query", "display_name"])


def pending_places() -> list[str]:
    """Fixed voting places in staging that are not in the cache yet."""
    places = pd.read_parquet(STAGING / "stg_voting_places.parquet")
    places = places[places.place_kind.isin(["advance", "election_day"])]
    done = set(load_cache()["voting_place_raw"])
    return [p for p in sorted(places["voting_place_raw"].unique()) if p not in done]


def main() -> None:
    cache = load_cache()
    todo = pending_places()
    print(f"{len(cache)} cached, {len(todo)} to geocode")
    if not todo:
        return

    geocoder = Nominatim(user_agent=USER_AGENT, timeout=15)
    geocode = RateLimiter(geocoder.geocode, min_delay_seconds=1.1, max_retries=2, error_wait_seconds=5, swallow_exceptions=True)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    new_rows = []
    for n, place in enumerate(todo, 1):
        hit, used = None, ""
        for q in queries_for(place):
            loc = geocode(q, country_codes="nz")
            if ok(loc):
                hit, used = loc, q
                break
        new_rows.append(
            {
                "voting_place_raw": place,
                "lat": hit.latitude if hit else None,
                "lon": hit.longitude if hit else None,
                "matched_query": used,
                "display_name": hit.address if hit else "",
            }
        )
        if n % 20 == 0 or n == len(todo):
            pd.concat([cache, pd.DataFrame(new_rows)], ignore_index=True).to_csv(CACHE, index=False)
            print(f"  {n}/{len(todo)}", flush=True)
    out = pd.concat([cache, pd.DataFrame(new_rows)], ignore_index=True)
    out.to_csv(CACHE, index=False)
    print(f"matched {out.lat.notna().sum()}/{len(out)}; unmatched need manual lat/lon in {CACHE}")


if __name__ == "__main__":
    main()
