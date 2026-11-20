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
