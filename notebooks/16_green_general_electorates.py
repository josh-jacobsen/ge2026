# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
# ---

# %% [markdown]
# # 16 – Green party vote in the general electorates, 2023 → 2026
# How the Green party vote changed across the general-roll electorates, with the seven Māori electorates left out. The Māori
# electorates saw a very large Green rise, which lifts the national figure; this notebook shows what the change looks like without them.
#
# **Measures** (party vote only, % of all valid party votes in the seat)
# * **Change in points** = 2026 share − 2023 share. **Relative change** = 2026 share ÷ 2023 share − 1, in %. A seat going from 10% to 11% is
#   +1 point and +10% relative. Points are the usual measure of a swing; relative change shows how much bigger a small base grew.
# * **Pooled** = all the seats' votes added together first (a seat counts in proportion to its votes). **Median/mean of seats** = each seat
#   counts once.
#
# **Data:** 2023 all votes (ordinary + special + overseas); 2026 final count, all votes (`out.csv` electorate totals), as in the other
# notebooks. 2023 electorates are matched to 2026 by name, with the Commission's list of renames (`electorates.PREDECESSOR`).
#
# **Read with care**
# * **Boundaries.** All 2026 seats were redrawn, and a few were renamed or merged. Seats are matched by name, so some changes mix voters
#   with territory. `comparable` marks seats whose 2023 and 2026 versions are close enough (notebook 02); section 4 repeats the headline on
#   those seats only.
# * **Ōhāriu** (general) was abolished. It has no 2026 seat, so it is not in the per-seat table; its 2023 votes are in the "all general votes
#   2023" line of section 2 (as in notebook 06's national figure), not in the like-for-like rows.
# * Two things move a share: Green votes and everyone else's votes. Section 3 splits the change into the two.
# * Ecological inference: a seat's change says nothing about how any individual voter changed their vote.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import electorates, plotstyle, vote_scope

PARTY = "Green Party"
VOTE_SCOPE, COUNT_STAGE = "all", "final"
FOCUS_SEATS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
GREEN, GREEN_LIGHT = "#098137", "#a8d5ba"
MARK = plotstyle.seat_markers(FOCUS_SEATS)
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)

# %% [markdown]
# ## 1. Load: Green party votes and all valid party votes per seat

# %%
pv = electorates.align_2023(vote_scope.load("stg_party_votes", VOTE_SCOPE, COUNT_STAGE))
print(vote_scope.describe(VOTE_SCOPE, COUNT_STAGE))
rel = pd.read_csv(ROOT / "data/reference/electorate_relationships_2026.csv").set_index("electorate_2026")
roll = rel.roll
assert (roll == "general").sum() == 64 and (roll == "maori").sum() == 7

g = pv.groupby(["election_year", "electorate"]).apply(
    lambda d: pd.Series({"green": d.loc[d.party == PARTY, "votes"].sum(), "valid": d.votes.sum()}), include_groups=False)
g = g.unstack("election_year")
seats = pd.DataFrame({
    "green_2023": g[("green", 2023)], "valid_2023": g[("valid", 2023)],
    "green_2026": g[("green", 2026)], "valid_2026": g[("valid", 2026)],
}).astype("Int64")
gone = seats[seats.green_2026.isna()].index.tolist()
print("2023 seats with no 2026 counterpart (not in the per-seat table):", gone)
seats = seats.reindex(roll.index)                       # the 71 seats of 2026
assert seats.notna().all().all(), seats[seats.isna().any(axis=1)]
seats = seats.astype(int)
seats["roll"] = roll
seats["comparable"] = rel.comparable.astype(bool)
seats["overlap"] = rel.primary_share           # % of the 2026 seat's votes from the 2023 seat it is compared with (renames included)
seats["relationship"] = rel.relationship
seats["compared_with_2023"] = rel.primary_2023
for y in (2023, 2026):
    seats[f"share_{y}"] = seats[f"green_{y}"] / seats[f"valid_{y}"] * 100
seats["change_pts"] = seats.share_2026 - seats.share_2023
seats["change_rel_pct"] = (seats.share_2026 / seats.share_2023 - 1) * 100
seats["focus"] = seats.index.isin(FOCUS_SEATS)

# the all-seat pooled shares must reproduce the official national Green party vote (11.6% in 2023, 14.1% in 2026)
nat = {y: seats[f"green_{y}"].sum() / seats[f"valid_{y}"].sum() * 100 for y in (2023, 2026)}
whole23 = g[("green", 2023)].sum() / g[("valid", 2023)].sum() * 100        # includes abolished Ōhāriu
print(f"Green party vote, all electorates: 2023 {whole23:.2f}% (incl. {', '.join(gone)}) | 2026 {nat[2026]:.2f}%")
assert abs(whole23 - 11.6) < 0.1 and abs(nat[2026] - 14.1) < 0.1, "national Green share changed: check the data"

# %% [markdown]
# ## 2. Headline: all electorates, general roll only, Māori electorates only
# Pooled shares. "General roll" is the answer to the question: the Green change once the Māori electorates are excluded.

# %%


def pooled(mask, label):
    s = seats[mask]
    a, b = s.green_2023.sum() / s.valid_2023.sum() * 100, s.green_2026.sum() / s.valid_2026.sum() * 100
    return pd.Series({"seats": len(s), "Green % 2023": a, "Green % 2026": b, "change (pts)": b - a, "relative change (%)": (b / a - 1) * 100,
                      "Green votes 2023": s.green_2023.sum(), "Green votes 2026": s.green_2026.sum()}, name=label)


gen = seats.roll == "general"
allseats = pd.Series(True, index=seats.index)
head = pd.DataFrame([
    pooled(allseats, "All 71 electorates (2026 seats)"),
    pooled(gen, "General roll only (64)"),
    pooled(seats.roll == "maori", "Māori electorates only (7)"),
    pooled(gen & seats.comparable, f"General roll, comparable boundaries ({int((gen & seats.comparable).sum())})"),
])
display(head.round(2))
gen_all23 = g.loc[[e for e in g.index if e in roll.index and roll[e] == "general" or e not in roll.index], ("green", 2023)].sum() / \
    g.loc[[e for e in g.index if e in roll.index and roll[e] == "general" or e not in roll.index], ("valid", 2023)].sum() * 100
print(f"All general votes 2023 including abolished Ōhāriu: {gen_all23:.2f}% (vs {head.loc['General roll only (64)', 'Green % 2023']:.2f}% on the 64 seats alone)")
print(f"Excluding the Māori electorates: the Green change is {head.iloc[1]['change (pts)']:+.2f} pts ({head.iloc[1]['relative change (%)']:+.1f}% relative), "
      f"against {head.iloc[0]['change (pts)']:+.2f} pts ({head.iloc[0]['relative change (%)']:+.1f}%) for all 71 seats.")

# %% [markdown]
# ## 3. Where the change came from: Green votes or everyone else's
# Pooled over the 64 general seats. A share can fall while Green votes rise if total votes rose faster.

# %%
s = seats[gen]
dec = pd.DataFrame({
    "2023": [s.green_2023.sum(), s.valid_2023.sum(), s.valid_2023.sum() - s.green_2023.sum()],
    "2026": [s.green_2026.sum(), s.valid_2026.sum(), s.valid_2026.sum() - s.green_2026.sum()],
}, index=["Green party votes", "all valid party votes", "everyone else"])
dec["change"] = dec["2026"] - dec["2023"]
dec["change %"] = dec["change"] / dec["2023"] * 100
display(dec.round(1))
print(f"Seats where the Green share rose: {(s.change_pts > 0).sum()} of {len(s)}; fell: {(s.change_pts < 0).sum()}.")
print(f"Change in points across the 64 seats: median {s.change_pts.median():+.2f}, mean {s.change_pts.mean():+.2f}, "
      f"min {s.change_pts.min():+.2f} ({s.change_pts.idxmin()}), max {s.change_pts.max():+.2f} ({s.change_pts.idxmax()})")
print(f"Relative change across the 64 seats: median {s.change_rel_pct.median():+.1f}%, mean {s.change_rel_pct.mean():+.1f}%")

# %% [markdown]
# ## 4. Every general electorate
# Sorted by change in points. `comparable` = the seat's 2023 and 2026 versions are close; `overlap` = share of the 2026 seat's votes that came
# from the 2023 seat it is compared with (`compared_with_2023`, which is the predecessor for renamed seats; notebook 02). Focus seats are marked.
# **The seats that merged or were redrawn most are the ones to distrust.** Wellington North, for example, is Wellington Central (55%) plus
# Ōhāriu (45%) but is compared with Wellington Central alone, so its drop of nearly 10 points is mostly the merge, not voters.

# %%
t = seats[gen].sort_values("change_pts", ascending=False)
t["rank"] = range(1, len(t) + 1)
cols = ["rank", "share_2023", "share_2026", "change_pts", "change_rel_pct", "green_2023", "green_2026", "compared_with_2023", "overlap", "comparable", "focus"]
display(t[cols].round(2))
print("Seats that are not comparable, with the biggest moves (read these as boundary effects first):")
display(t[~t.comparable].reindex(t[~t.comparable].change_pts.abs().sort_values(ascending=False).index).head(8)[["share_2023", "share_2026", "change_pts", "relationship"]].round(1))

comp = t[t.comparable]
print(f"On the {len(comp)} comparable general seats: pooled change {head.iloc[3]['change (pts)']:+.2f} pts; median of seats {comp.change_pts.median():+.2f}; "
      f"{(comp.change_pts > 0).sum()} up, {(comp.change_pts < 0).sum()} down")
print("Focus seats: rank of 64 by change in points")
display(t.loc[[e for e in FOCUS_SEATS if e in t.index], ["rank", "share_2023", "share_2026", "change_pts", "change_rel_pct"]].round(2))

# %% [markdown]
# ## 5. Charts
# Change in points for every general seat (focus seats in bold; the dashed line is the pooled general-roll change), and whether seats with a
# higher Green share in 2023 changed more or less.

# %%
order = t.index[::-1]
fig, ax = plt.subplots(figsize=(8, 15))
ax.barh(range(len(order)), t.loc[order, "change_pts"], color=[GREEN if t.loc[e, "comparable"] else GREEN_LIGHT for e in order])
ax.set_yticks(range(len(order)), order, fontsize=8)
for tick, name in zip(ax.get_yticklabels(), order):
    if name in FOCUS_SEATS:
        tick.set_fontweight("bold")
ax.axvline(0, color="black", lw=.8)
ax.axvline(head.iloc[1]["change (pts)"], color="#444444", ls="--", lw=1, label=f"pooled general roll {head.iloc[1]['change (pts)']:+.2f}")
ax.set_xlabel("change in Green party vote share, 2023 → 2026 (points)")
ax.set_title("Green party vote change, 64 general electorates\n(dark = comparable boundaries, light = boundaries changed more)")
ax.legend(loc="lower right"); ax.grid(axis="x", alpha=.3)
plt.tight_layout(); plt.show()

fig, ax = plt.subplots(figsize=(7.5, 5.5))
other = t[~t.focus]
ax.scatter(other[other.comparable].share_2023, other[other.comparable].change_pts, s=22, color=GREEN, alpha=.7, label="other seats, comparable boundaries")
ax.scatter(other[~other.comparable].share_2023, other[~other.comparable].change_pts, s=22, color=GREEN_LIGHT, edgecolor=GREEN, lw=.6, label="boundaries changed more")
for e in FOCUS_SEATS:
    if e in t.index:
        ax.scatter(t.loc[e, "share_2023"], t.loc[e, "change_pts"], s=90, marker=MARK[e], color=GREEN, edgecolor="black", label=e, zorder=3)
ax.axhline(0, color="black", lw=.8); ax.axhline(head.iloc[1]["change (pts)"], color="#444444", ls="--", lw=1)
ax.set_xlabel("Green party vote share 2023 (%)"); ax.set_ylabel("change in share 2023 → 2026 (points)")
ax.set_title("Did strong Green seats gain more? 64 general electorates"); ax.grid(alpha=.3); ax.legend(fontsize=8)
plt.tight_layout(); plt.show()
r_all = np.corrcoef(t.share_2023, t.change_pts)[0, 1]
r_comp = np.corrcoef(t[t.comparable].share_2023, t[t.comparable].change_pts)[0, 1]
print(f"Correlation between a seat's 2023 Green share and its change: {r_all:+.2f} on all 64 seats, {r_comp:+.2f} on the {int(t.comparable.sum())} comparable seats.")
print("The strongest-Green seats rose least or fell. Part of that is ordinary regression to the mean (a seat that was unusually high in one election tends to be less extreme in the next); it does not show why. A description of the pattern, not a cause.")

# %% [markdown]
# ## 6. Save
# One row per general electorate (and the Māori electorates, marked by `roll`), for a spreadsheet.

# %%
out = seats.sort_values("change_pts", ascending=False)
out.round(3).to_csv(ROOT / "data/staging/green_party_change_by_electorate.csv")
print("saved data/staging/green_party_change_by_electorate.csv", out.shape)
