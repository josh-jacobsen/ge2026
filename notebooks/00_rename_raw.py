# %% [markdown]
# # 00 – Rename raw files from their contents
# Downloads have generic or duplicated names (`party-votes-by-voting-place-1(1).csv`, `07_Dunedin(1).xlsx`).
# This renames each file using the **electorate (and file type) read from inside it**:
#
# * 2023 CSV  → `ge2023_<electorate>_<party|candidate>.csv`
# * 2026 XLSX → `ge2026_<electorate>.xlsx` (Party and Candidate sheets live in one workbook)
#
# Byte-identical duplicate downloads go to `_duplicates/`. Nothing is overwritten or deleted. Safe to re-run.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import etl

YEARS = (2023, 2026)

# %% [markdown]
# ## 1. What is in each folder? (current name → recognised electorate/kind)

# %%
for year in YEARS:
    base = etl.RAW / f"ge{year}"
    found = etl.raw_files(year)
    unknown = [p for p in base.rglob("*") if p.is_file() and p.name != ".DS_Store" and p not in {a for a, _ in found}
               and not any(part.startswith("_") for part in p.relative_to(base).parts)]
    print(f"{year}: {len(found)} recognised result files, {len(unknown)} not recognised")
    for p in unknown:
        print("   not recognised:", p.relative_to(base))

# %% [markdown]
# ## 2. Dry run – review the plan

# %%
for year in YEARS:
    print(f"--- {year}")
    etl.rename_raw(year, dry_run=True)

# %% [markdown]
# ## 3. Apply

# %%
for year in YEARS:
    print(f"--- {year}")
    etl.rename_raw(year)

# %% [markdown]
# ## 4. Check: one file per electorate (2023: one party + one candidate each)

# %%
rows = []
for year in YEARS:
    for p, _ in etl.raw_files(year):
        if year == 2023:
            rows.append({"year": year, "electorate": etl.electorate_of_csv(p), "kind": etl.csv_kind(p)})
        else:
            rows.append({"year": year, "electorate": etl.electorate_of_xlsx(p), "kind": "workbook"})
chk = pd.DataFrame(rows).value_counts().unstack(fill_value=0)
display(chk.groupby(level="year").sum())
# 2023: one party file per electorate, and one candidate file too, except Port Waikato (its 2023 election was postponed,
# so there are no candidate results for it). 2026: exactly one workbook per electorate.
NO_CANDIDATE_FILE_2023 = {"Port Waikato"}
c23, c26 = chk.loc[2023], chk.loc[2026]
bad = pd.concat([
    c23[(c23.party != 1) | ((c23.candidate != 1) & ~c23.index.isin(NO_CANDIDATE_FILE_2023))],
    c23[c23.index.isin(NO_CANDIDATE_FILE_2023) & (c23.candidate != 0)],
    c26[c26.workbook != 1],
])
assert bad.empty, bad

# %% [markdown]
# ## 5. Electorates present in one year but not the other
# 2026 uses new boundaries (e.g. Botany, Takanini, Wigram), so electorate-level comparison is only
# possible where names match; voting places are compared by location instead (notebook 03).

# %%
e = {y: {p.name.split("_", 1)[1].rsplit(".", 1)[0].rsplit("_", 1)[0] if y == 2023 else p.stem.split("_", 1)[1]
         for _, p in etl.raw_files(y)} for y in YEARS}
print("only 2023:", sorted(e[2023] - e[2026]))
print("only 2026:", sorted(e[2026] - e[2023]))

# %% [markdown]
# ## 6. Final 2026 results (when released)
# Save the Commission's final files in `data/raw/ge2026_final/`, then run this cell to give them canonical names. They are
# kept apart from the preliminary files (`data/raw/ge2026/`) so both counts stay available; notebook 01 tags every row
# with its `count_stage`.

# %%
if etl.raw_dir(2026, "final").exists():
    etl.rename_raw(2026, dry_run=True, stage="final")      # review, then re-run with dry_run=False
else:
    print("no data/raw/ge2026_final/ folder yet")
