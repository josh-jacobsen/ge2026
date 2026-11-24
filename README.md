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
3. `03_geocode`: Nominatim lookups (cached, resumable); flags pins far from their electorate's other venues (wrong-city hits); fix misses and outliers by hand in the cache CSV
4. `04_analysis`: shares, swing, voting-place maps (set `FOCUS` to any party)
5. `05_electorate_analysis`: electorate-level rankings, swing, leading party and flips, party heatmap (needs only notebooks 01–02, no geocoding)

Raw data goes in `data/raw/ge2023/` (CSV) and `data/raw/ge2026/` (XLSX). CLI equivalents:
`python src/etl.py --rename-only [--dry-run]`, `python src/etl.py`, `python src/geocode.py`.

## Tests
    uv run pytest                          # everything (~15 s)
    uv run pytest tests/unit               # fast logic tests, no raw data needed (~0.1 s)
    uv run pytest tests/official_results   # staging vs the Commission's published figures

    tests/
      unit/                  venue aggregation, distance matching, party-name decisions
      official_results/      rebuilds staging from data/raw and checks it against official figures
        test_2026_national.py    17 party totals, 2,418,565 votes, 71 electorates, seat arithmetic
        test_2023_national.py    17 party totals, 2,851,211 votes, 72 electorates, seat arithmetic, every electorate vs the turnout table
        test_staged_party_names.py
        data/                    expected official figures (JSON); more in data/raw/*/_turnout/
        conftest.py              builds the staging tables once per run

## Caveats
- 2026 data is **preliminary, ordinary votes only**. Compare `advance` + `election_day` rows only.
- Candidate -> party mapping exists for 2023 only (`stg_candidate_party`); 2026 needs adding.
- Boundaries changed in 2025: the electorate-level comparison matches by name, using the Commission's rename list for the
  10 renamed seats (`electorates.PREDECESSOR`, e.g. East Coast -> East Cape), so all 71 are compared. Many seats were also
  redrawn; `electorates.seat_overlap()` gives the % of each 2026 seat that came from the 2023 seat it is compared with
  (low for Glendene, Kapiti, Kenepuru, Wellington North, Mt Roskill). Voting-place matching in notebook 04 is boundary-independent.
- The crosswalk is a proxy built from election-day venue overlap, not the Commission's official meshblock crosswalk.
