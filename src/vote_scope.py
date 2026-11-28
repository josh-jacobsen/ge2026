"""Which votes and which count a notebook uses: one switch instead of a filter in every notebook.

* ``scope``  "ordinary" = advance + election-day votes at voting places (the like-for-like basis while 2026 is preliminary).
             "all"      = every vote counted: ordinary + mobile teams + special + overseas (everything except the
                          'total' rows). Special and overseas votes belong to an electorate, not a voting place, so
                          they can only feed electorate-level results, never voting-place maps.
* ``stage``  which 2026 count: "preliminary" (data/raw/ge2026) or "final" (data/raw/ge2026_final/out.csv: one row per
             electorate and party/candidate, special votes included, no voting places, so it only serves scope "all").
             2023 results are final and always included.

``load`` refuses to run when the choice would silently give a misleading answer, e.g. scope "all" before special
votes have been loaded for both years (2026 would just be ordinary votes again).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from places import ORDINARY

STAGING = Path(__file__).resolve().parents[1] / "data" / "staging"
SCOPES = ("ordinary", "all")
SPECIAL_KINDS = ("special", "overseas", "electorate_total")  # electorate_total (final out.csv) already includes them


def load(table: str = "stg_party_votes", scope: str = "ordinary", stage: str = "preliminary", staging: Path = STAGING) -> pd.DataFrame:
    """Staging rows for 2023 (final) and 2026 (`stage`), restricted to the votes in `scope`."""
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}, not {scope!r}")
    df = pd.read_parquet(staging / f"{table}.parquet")
    if "count_stage" not in df:
        raise ValueError("staging has no count_stage column: re-run notebook 01 (or `uv run python src/etl.py`)")
    df = df[(df.election_year == 2023) | (df.count_stage == stage)]
    if not (df.election_year == 2026).any():
        raise ValueError(f"no 2026 {stage} results in {table}: add them to data/raw/{'ge2026_final' if stage == 'final' else 'ge2026'} and re-run notebook 01")
    if scope == "ordinary":
        out = df[df.place_kind.isin(ORDINARY)].reset_index(drop=True)
        if not (out.election_year == 2026).any():
            raise ValueError(
                f"no ordinary-vote rows for 2026 {stage}: the final results are electorate totals including special votes "
                "(data/raw/ge2026_final/out.csv), so use scope 'all', or stage 'preliminary' for ordinary votes"
            )
        return out
    for year, d in df.groupby("election_year"):
        if not d.place_kind.isin(SPECIAL_KINDS).any():
            raise ValueError(
                f"scope 'all' needs special votes, but {year} ({stage}) has none in {table}: it would silently equal "
                "'ordinary'. Load results that include special votes, or use scope 'ordinary'."
            )
    return df[df.place_kind != "total"].reset_index(drop=True)


def describe(scope: str, stage: str) -> str:
    what = "ordinary votes only (advance + election day)" if scope == "ordinary" else "all votes (ordinary + special + overseas)"
    return f"2023 final vs 2026 {stage}; {what}"
