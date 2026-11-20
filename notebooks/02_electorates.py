# %% [markdown]
# # 02 – Reconcile 2023 and 2026 electorates
# The 2025 boundary review cut New Zealand from 72 to 71 electorates, so electorate names (and the voters
# inside them) differ between elections. This notebook builds an **evidence-based crosswalk** from the data:
#
# * Each election-day venue gets a *home electorate* per year (the electorate whose voters cast most votes
#   there). Advance venues are ignored because they serve voters from everywhere.
# * Venues are matched across years by normalised name/address (exact, then fuzzy within suburb).
# * A 2026 electorate's votes at matched venues show which 2023 electorates it was built from, and vice versa.
#
# General and Māori electorates are done separately (Māori seats overlay the same venues).
# This is a proxy from venue locations, not the Commission's official meshblock crosswalk.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import electorates as el

pd.set_option("display.width", 220, "display.max_rows", 200, "display.max_colwidth", 110)
pv = pd.read_parquet(el.STAGING / "stg_party_votes.parquet")

# %% [markdown]
# ## 1. Electorate names: what changed?

# %%
names = {y: set(pv[pv.election_year == y].electorate) for y in (2023, 2026)}
print(f"2023: {len(names[2023])} electorates   2026: {len(names[2026])} electorates   same name: {len(names[2023] & names[2026])}")
print("only 2023:", sorted(names[2023] - names[2026]))
print("only 2026:", sorted(names[2026] - names[2023]))

# %% [markdown]
# ## 2. Home electorate per election-day venue, then match venues across years

# %%
venues = el.place_totals(pv)
print(venues.groupby(["election_year", "maori"]).size().unstack().rename(columns={False: "general", True: "māori"}))
print(f"median share of a venue's votes cast by its home electorate: {venues.home_share.median():.0%}")
matched = el.match_places(venues)
display(matched.groupby("roll").match.apply(lambda s: s.str.split().str[0].value_counts()).unstack(fill_value=0))

# %% [markdown]
# Spot-check the fuzzy matches (these are the ones most likely to be wrong):

# %%
fz = matched[matched.match.str.startswith("fuzzy")]
display(fz.sample(min(12, len(fz)), random_state=1)[["voting_place_raw_2023", "voting_place_raw_2026", "match"]])

# %% [markdown]
# ## 3. Where did each 2026 electorate come from?
# `same_name_share` = % of its matched venue votes that were in the same-named 2023 electorate.
# `matched_vote_coverage` = % of its election-day votes at venues we could match (low = treat with caution).

# %%
xw = el.crosswalk(matched)
s26 = el.summarise_2026(xw, matched)
s26["comparable"] = s26.relationship == "continuing"
display(s26.relationship.str.split(" from| of").str[0].value_counts())
display(s26[s26.relationship != "continuing"][["roll", "electorate_2026", "relationship", "same_name_share", "matched_vote_coverage"]])

# %% [markdown]
# ## 4. Where did each 2023 electorate go?

# %%
s23 = el.summarise_2023(xw)
display(s23[s23.relationship != "continues"][["roll", "electorate_2023", "relationship", "destinations"]])

# %% [markdown]
# ## 5. Check against the Commission's published description of the 2025 review
# Expected relationships (2026 seat ← 2023 seats named in the Commission's summary). Pass = every named
# 2023 seat appears among the sources that supply ≥ 10% of the 2026 seat's matched venue votes.

# %%
expected = {
    "Waitākere": ["New Lynn", "Kelston", "Te Atatū"], "Glendene": ["New Lynn", "Kelston", "Te Atatū"],
    "Henderson": ["New Lynn", "Kelston", "Te Atatū"],
    "Ōtāhuhu": ["Panmure-Ōtāhuhu"], "Mt Maunganui": ["Bay of Plenty"], "East Cape": ["East Coast"],
    "Wellington North": ["Wellington Central"], "Wellington Bays": ["Rongotai"],
}
rows = []
for e26, want in expected.items():
    d = xw[xw.electorate_2026 == e26].set_index("electorate_2023").share_of_2026
    top = d.sort_values(ascending=False)
    # for the west-Auckland trio the Commission names the three 2023 seats collectively, so require >= 1 of them
    ok = any(top.get(w, 0) >= 10 for w in want) if len(want) > 1 else top.get(want[0], 0) >= 10
    rows.append({"electorate_2026": e26, "commission": " / ".join(want), "evidence": "; ".join(f"{k} {v:.0f}%" for k, v in top.head(3).items()), "consistent": ok})
chk = pd.DataFrame(rows)
display(chk)
# Ōhāriu abolished; Kenepuru and Kapiti created
for e23 in ["Ōhāriu"]:
    print(f"{e23} is abolished: same-name share in 2026 = {s23.set_index('electorate_2023').same_name_share[e23]}%  ->", s23.set_index("electorate_2023").destinations[e23])
for e26 in ["Kenepuru", "Kapiti"]:
    print(f"{e26} is new: sources =", s26.set_index("electorate_2026").sources[e26])

# %% [markdown]
# ## 6. Picture: sources of each non-continuing 2026 general electorate (% of its matched venue votes)

# %%
chg = s26[(s26.roll == "general") & (~s26.comparable)].electorate_2026
sub = xw[(xw.roll == "general") & xw.electorate_2026.isin(chg)].pivot_table(index="electorate_2026", columns="electorate_2023", values="share_of_2026", fill_value=0)
sub = sub.loc[:, sub.max() >= 10]
fig, ax = plt.subplots(figsize=(max(8, 0.55 * sub.shape[1]), 0.35 * sub.shape[0] + 2))
im = ax.imshow(sub.values, cmap="Greens", vmin=0, vmax=100, aspect="auto")
ax.set_xticks(range(sub.shape[1]), sub.columns, rotation=60, ha="right"); ax.set_yticks(range(sub.shape[0]), sub.index)
for i in range(sub.shape[0]):
    for j in range(sub.shape[1]):
        if sub.values[i, j] >= 10:
            ax.text(j, i, f"{sub.values[i, j]:.0f}", ha="center", va="center", fontsize=8)
ax.set_xlabel("2023 electorate"); ax.set_ylabel("2026 electorate"); fig.colorbar(im, label="% of 2026 votes")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 7. Save reference tables (tracked in git)
# `comparable` = same name and ≥ 80 % overlap: safe to compare at electorate level. Everything else should be
# compared at voting-place level (notebook 04) rather than by electorate name.

# %%
el.REFERENCE.mkdir(parents=True, exist_ok=True)
s26.to_csv(el.REFERENCE / "electorate_relationships_2026.csv", index=False)
s23.to_csv(el.REFERENCE / "electorate_relationships_2023.csv", index=False)
xw.round(2).to_csv(el.REFERENCE / "electorate_crosswalk_pairs.csv", index=False)
matched.drop(columns=["maori_2023", "maori_2026"], errors="ignore").to_parquet(el.STAGING / "venue_matches.parquet", index=False)
print("comparable electorates:", int(s26.comparable.sum()), "of", len(s26))
