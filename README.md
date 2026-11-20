# NZ election analysis: 2026 vs 2023

Voting-place level comparison for East Coast Bays, North Shore, Northcote and Upper Harbour.

## Setup
    uv sync

## Notebooks (`notebooks/`), run in order
Each notebook is a `.py` (`# %%` cells, diff-friendly) paired with an `.ipynb`; open either in VS Code
and pick the `.venv` kernel. Regenerate the ipynb after editing the .py: `uv run jupytext --to ipynb notebooks/*.py`.

0. `00_rename_raw`: rename 2023 CSVs from their contents; park identical duplicates in `_duplicates/`
1. `01_staging`: raw CSV/XLSX -> tidy staging tables + reconciliation against official totals
2. `02_geocode`: Nominatim lookups (cached, resumable); fix misses by hand in the cache CSV
3. `03_analysis`: shares, swing, voting-place maps (set `FOCUS` to any party)

Raw data goes in `data/raw/ge2023/` (CSV) and `data/raw/ge2026/` (XLSX). CLI equivalents:
`python src/etl.py --rename-only [--dry-run]`, `python src/etl.py`, `python src/geocode.py`.

## Caveats
- 2026 data is **preliminary, ordinary votes only**. Compare `advance` + `election_day` rows only.
- Candidate -> party mapping exists for 2023 only (`stg_candidate_party`); 2026 needs adding.
- Electorate numbers differ between years; join on electorate name.
