# NZ election analysis: 2026 vs 2023

Voting-place level comparison.

## Setup
    uv sync

## Notebooks (`notebooks/`), run in order
Each notebook is a `.py` (`# %%` cells, diff-friendly) paired with an `.ipynb`; open either in VS Code
and pick the `.venv` kernel. Regenerate the ipynb after editing the .py: `uv run jupytext --to ipynb notebooks/*.py`.

0. `00_rename_raw`: rename 2023 CSVs from their contents; park identical duplicates in `_duplicates/`
1. `01_staging`: raw CSV/XLSX -> tidy staging tables + reconciliation against official totals
2. `02_electorates`: reconcile 2023 (72) and 2026 (71) electorates after the 2025 boundary review; writes `data/reference/`
3. `03_geocode`: Nominatim lookups (cached, resumable); fix misses by hand in the cache CSV
4. `04_analysis`: shares, swing, voting-place maps (set `FOCUS` to any party)

Raw data goes in `data/raw/ge2023/` (CSV) and `data/raw/ge2026/` (XLSX). CLI equivalents:
`python src/etl.py --rename-only [--dry-run]`, `python src/etl.py`, `python src/geocode.py`.

## Tests
    uv run pytest

Staging is rebuilt from `data/raw` and checked against the Commission's published national figures:
`tests/test_national_2026.py` (17 party totals, 2,418,565 votes, 71 electorates, seat arithmetic) and
`tests/test_national_2023.py` (72 electorates, national and general/Māori totals, every electorate total vs the
turnout table). Expected figures live in `tests/data/` and `data/raw/*/_turnout/`. One 2023 test skips until the
2023 national party table is saved as `data/raw/ge2023/_turnout/ge2023_party_votes_national.csv` (`party,party_votes`).

## Caveats
- 2026 data is **preliminary, ordinary votes only**. Compare `advance` + `election_day` rows only.
- Candidate -> party mapping exists for 2023 only (`stg_candidate_party`); 2026 needs adding.
- Boundaries changed in 2025: only 57 of 71 electorates are `comparable` between years (same name and >= 80% venue overlap,
  see `data/reference/electorate_relationships_2026.csv`). Compare the rest at voting-place level, not by electorate name.
- The crosswalk is a proxy built from election-day venue overlap, not the Commission's official meshblock crosswalk.
