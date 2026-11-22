# %% [markdown]
# # 01 – Staging tables
# Parse the raw 2023 CSVs and 2026 XLSX files into tidy long-format tables and reconcile them
# against the official totals. Writes `data/staging/*.parquet` (and `.csv`).

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import etl

pd.set_option("display.width", 200, "display.max_columns", 30)

# %%
tables = etl.build()
for name, df in tables.items():
    print(f"{name:22s} {df.shape}")
tables["stg_party_votes"].head()

# %% [markdown]
# ## Reconciliation
# `places_sum` (every non-total row) must equal the official `total` row. `diff` should be 0 everywhere.

# %%
chk = etl.checks(tables)
display(chk)
assert (chk["diff"] == 0).all(), "staging does not reconcile with official totals"

# %% [markdown]
# ## Second check: independent 2023 electorate totals
# The check above compares place rows to the total row *in the same file*, so it only proves the parser is
# faithful. The Commission's separate turnout table (`data/raw/ge2023/_turnout/`) gives valid party votes per
# electorate from a different publication, so a match here also confirms the source totals themselves.
# (2026 has no equivalent table yet. Its check is internal only.)

# %%
chk2 = etl.checks_turnout_2023(tables)
display(chk2[chk2["diff"] != 0] if (chk2["diff"] != 0).any() else chk2.describe().loc[["count", "min", "max"]])
missing = chk2[chk2[["valid_total", "staging_total"]].isna().any(axis=1)]
assert missing.empty, f"electorates missing from one side:\n{missing}"
assert (chk2["diff"] == 0).all(), "staging totals differ from the Commission turnout table"

_, nat = etl.load_turnout_2023()
ours_nat = int(chk2["staging_total"].sum())
print(f"{len(chk2)} electorates match; national valid party votes: staging {ours_nat:,} vs Commission {nat['combined']:,}")
assert ours_nat == nat["combined"] == nat["general"] + nat["maori"]

# %% [markdown]
# ## Second check: published 2023 national party totals
# Same idea for 2023 (`data/raw/ge2023/_turnout/ge2023_party_votes_national.csv`, the official result).

# %%
chk4 = etl.checks_party_totals(tables, 2023)
display(chk4)
assert not chk4[["party_votes", "staging_votes"]].isna().any().any(), "party present on only one side"
assert (chk4["diff"] == 0).all(), "2023 party totals differ from the published national table"
print(f"{len(chk4)} parties match; national total {int(chk4.staging_votes.sum()):,}")

# %% [markdown]
# ## Second check: published 2026 national party totals
# Party votes summed over our 71 parsed electorate totals must equal the Commission's published national table
# (`data/raw/ge2026/_turnout/`, preliminary). This is independent of the per-electorate files.

# %%
chk3 = etl.checks_party_totals_2026(tables)
display(chk3)
assert not chk3[["party_votes", "staging_votes"]].isna().any().any(), "party present on only one side"
assert (chk3["diff"] == 0).all(), "2026 party totals differ from the published national table"
print(f"{len(chk3)} parties match; national total {int(chk3.staging_votes.sum()):,}")

# %% [markdown]
# ## What is in each election?
# 2026 is **preliminary, ordinary votes only** (no special/overseas votes), so compare
# `advance` + `election_day` rows only. 2023 includes special votes as separate `place_kind`s.

# %%
pv = tables["stg_party_votes"]
display(pv.groupby(["election_year", "place_kind"])["votes"].sum().unstack(fill_value=0))

# %% [markdown]
# ## Party names by year (check the alias map in `etl.PARTY_ALIASES`)

# %%
parties = pv.groupby(["party", "election_year"])["votes"].sum().unstack()
display(parties.sort_values(2026, ascending=False))

# %%
etl.write(tables)
print("written to", etl.STAGING)
