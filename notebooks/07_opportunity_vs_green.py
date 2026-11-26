# %% [markdown]
# # 07 – Did the rise of the Opportunity Party (TOP) cost the Greens? North Shore, Northcote, East Coast Bays, Upper Harbour
# **Theory:** TOP's jump in 2026 took party votes that would otherwise have gone to the Green Party.
#
# Four electorates are too few to test this seat by seat, so the evidence comes from the **voting places inside them**:
# where TOP rose more at a place, did the Green share rise *less*? Places are matched across years by exact name.
#
# What this can and cannot show
# * A negative relationship is **consistent with** the theory, not proof. Votes are anonymous, so we only see place
#   totals ("ecological inference"). Places where TOP did well differ in other ways too, and TOP's gain could have come
#   from Labour, National or NZ First voters with Greens unaffected.
# * Shares add to 100, so every gain is someone else's loss. The **placebo** section compares Green with the other parties
#   and with what an even draw from every party would give.
# * Direct evidence needs voter-level data, such as the NZ Election Study.
# * Ordinary votes only (`advance` + `election_day`): 2026 is preliminary with no special votes. Shares, not counts.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import electorates, vote_scope

GREEN, TOP = "Green Party", "The Opportunities Party (TOP)"
FOCUS_SEATS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
VOTE_SCOPE = "ordinary"    # section 1 (electorate level): "ordinary" or "all" (adds special + overseas votes)
COUNT_STAGE = "preliminary"  # section 1: 2026 count, "preliminary" or "final"
PLACE_STAGE = "preliminary"  # sections 2+ (voting places) are ordinary votes only: specials have no location
MIN_VOTES = 50         # ignore places with fewer ordinary party votes than this in either year (shares get noisy)
N_BOOT = 2000          # bootstrap resamples for confidence intervals
rng = np.random.default_rng(7)
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 100)

pv_scope = electorates.align_2023(vote_scope.load("stg_party_votes", VOTE_SCOPE, COUNT_STAGE))      # section 1
pv = electorates.align_2023(vote_scope.load("stg_party_votes", "ordinary", PLACE_STAGE))            # voting places
print("Electorate level:", vote_scope.describe(VOTE_SCOPE, COUNT_STAGE))
print("Voting places:  ", vote_scope.describe("ordinary", PLACE_STAGE))


def ols(x, y, w=None):
    """Slope and intercept of y on x (optionally weighted)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    w = np.ones_like(x) if w is None else np.asarray(w, float)
    xm, ym = np.average(x, weights=w), np.average(y, weights=w)
    b = np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2)
    return b, ym - b * xm


def boot_slope(d, x, y, w=None):
    """95 % bootstrap interval for the slope, resampling places."""
    out = []
    for _ in range(N_BOOT):
        s = d.iloc[rng.integers(0, len(d), len(d))]
        out.append(ols(s[x], s[y], None if w is None else s[w])[0])
    return np.percentile(out, [2.5, 97.5])


# %% [markdown]
# ## 1. The four seats against the country
# Party-vote share (ordinary votes). `swing` = 2026 − 2023 in percentage points.

# %%
share = pv_scope.groupby(["election_year", "electorate", "party"]).votes.sum().unstack("party").fillna(0)
share = share.div(share.sum(axis=1), axis=0) * 100
nat = pv_scope.groupby(["election_year", "party"]).votes.sum().unstack("party")
nat = nat.div(nat.sum(axis=1), axis=0) * 100
big = list(nat.loc[2026].sort_values(ascending=False).index[:7])          # the seven biggest parties in 2026
big_other = [p for p in big if p != TOP]

rows = []
for seat in FOCUS_SEATS:
    rows.append({"area": seat, **{f"{lab}_{y}": share.loc[(y, seat), p] for lab, p in (("green", GREEN), ("top", TOP)) for y in (2023, 2026)}})
rows.append({"area": "national", **{f"{lab}_{y}": nat.loc[y, p] for lab, p in (("green", GREEN), ("top", TOP)) for y in (2023, 2026)}})
tab = pd.DataFrame(rows).set_index("area")
tab["green_swing"] = tab.green_2026 - tab.green_2023
tab["top_swing"] = tab.top_2026 - tab.top_2023
display(tab.round(2))

# %%
sw_all = pd.DataFrame({seat: share.loc[2026].loc[seat, big] - share.loc[2023].loc[seat, big] for seat in FOCUS_SEATS}).T
sw_all.loc["national"] = nat.loc[2026, big] - nat.loc[2023, big]
ax = sw_all.T.plot.bar(figsize=(11, 4.5), width=0.85)
ax.axhline(0, color="black", lw=0.8); ax.set_ylabel("Swing 2023 → 2026 (points)")
ax.set_title("Party-vote swing by party: the four seats vs national"); ax.legend(fontsize=8)
plt.xticks(rotation=30, ha="right"); plt.tight_layout(); plt.show()

# %% [markdown]
# ## 2. Matching voting places across years
# Each place's results are summed over every electorate that lists it, advance and election day together, and places are
# matched by normalised name (`electorates.venue_key`). A place belongs to the focus seat where most of its votes were
# cast in 2026. Places renamed or replaced between elections drop out; the coverage line says how much is left.

# %%
raw = pv[["voting_place_raw"]].drop_duplicates()
keys = raw.voting_place_raw.map(electorates.venue_key)
raw["suburb_key"], raw["venue_key"] = keys.str[0], keys.str[1]
v = pv.merge(raw, on="voting_place_raw")
cols = ["election_year", "suburb_key", "venue_key"]
total = v.groupby(cols).votes.sum().rename("total")
by_party = v[v.party.isin(big)].groupby(cols + ["party"]).votes.sum().unstack("party").reindex(total.index).fillna(0)
pct = by_party.div(total, axis=0) * 100
home = v.groupby(cols + ["electorate"]).votes.sum().reset_index().sort_values("votes").drop_duplicates(cols, keep="last")
home = home.set_index(cols).electorate

p23, p26 = pct.xs(2023, level="election_year"), pct.xs(2026, level="election_year")
t23, t26 = total.xs(2023, level="election_year"), total.xs(2026, level="election_year")
h26 = home.xs(2026, level="election_year")
in_focus = h26[h26.isin(FOCUS_SEATS)]
ven = pd.DataFrame({"electorate": in_focus, "total_23": t23.reindex(in_focus.index), "total_26": t26.reindex(in_focus.index)}).dropna()
ven = ven[(ven.total_23 >= MIN_VOTES) & (ven.total_26 >= MIN_VOTES)]
for p in big:
    ven[f"{p}_23"], ven[f"{p}_26"] = p23[p].reindex(ven.index), p26[p].reindex(ven.index)
    ven[f"{p}_swing"] = ven[f"{p}_26"] - ven[f"{p}_23"]
ven["green"], ven["top"] = ven[f"{GREEN}_swing"], ven[f"{TOP}_swing"]

seat_votes = t26.reindex(in_focus.index).groupby(in_focus).sum()
cover = pd.DataFrame({"places 2026": in_focus.value_counts(), "places matched": ven.electorate.value_counts(),
                      "matched % of seat's place votes": ven.groupby("electorate").total_26.sum() / seat_votes * 100})
display(cover.reindex(FOCUS_SEATS).round(0))
assert len(ven) >= 20, "too few matched places to analyse"

# %% [markdown]
# ## 3. Green swing against TOP swing, place by place
# Slope −1 would mean each point TOP gained at a place cost the Greens a point; 0 means no relationship. "Within seat"
# subtracts each seat's average swing first, so it asks whether, *inside the same electorate*, places where TOP rose more
# saw Green rise less. Weighted by 2026 votes. Intervals resample places (few places per seat, so they are wide).

# %%
ven["green_w"] = ven.green - ven.groupby("electorate").green.transform("mean")
ven["top_w"] = ven.top - ven.groupby("electorate").top.transform("mean")
rows = []
for label, d, x, y in [("all four seats, raw", ven, "top", "green"), ("all four seats, within seat", ven, "top_w", "green_w")] + \
                      [(seat, ven[ven.electorate == seat], "top", "green") for seat in FOCUS_SEATS]:
    if len(d) < 5:
        continue
    b, _a = ols(d[x], d[y], d.total_26)
    lo, hi = boot_slope(d, x, y, "total_26")
    rows.append({"group": label, "places": len(d), "slope": b, "ci_low": lo, "ci_high": hi, "corr": d[x].corr(d[y])})
slopes = pd.DataFrame(rows).set_index("group")
display(slopes.round(2))

# %%
fig, ax = plt.subplots(figsize=(8, 6))
for seat, color in zip(FOCUS_SEATS, ["#1b7f4b", "#d9731a", "#4c72b0", "#8172b2"]):
    d = ven[ven.electorate == seat]
    ax.scatter(d.top, d.green, s=np.sqrt(d.total_26) * 1.2, alpha=0.6, color=color, label=f"{seat} ({len(d)})")
b, a = ols(ven.top, ven.green, ven.total_26)
xs = np.linspace(ven.top.min(), ven.top.max(), 10)
ax.plot(xs, a + b * xs, color="black", lw=1.2, label=f"fit, all places (slope {b:+.2f})")
ax.axhline(0, color="grey", lw=0.5); ax.axvline(0, color="grey", lw=0.5)
ax.set_xlabel("TOP swing at the place (points)"); ax.set_ylabel("Green swing at the place (points)")
ax.set_title("Voting places in the four seats: Green swing vs TOP swing"); ax.legend(fontsize=8)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 4. Placebo: is Green special, or does everyone lose where TOP gains?
# If TOP had drawn evenly from every party, each party's within-seat slope would equal minus its own share divided by the
# non-TOP share (`if proportional`). A slope much more negative than that means the party lost out to TOP more than its
# size explains. Zero or positive means TOP's rise at a place did not come at that party's expense.

# %%
rows = []
for party in big_other:
    d = ven.assign(y=ven[f"{party}_swing"], w=ven.total_26)
    d["y"] = d.y - d.groupby("electorate").y.transform("mean")
    b, _a = ols(d.top_w, d.y, d.w)
    lo, hi = boot_slope(d, "top_w", "y", "w")
    prop = -np.average(d[f"{party}_23"], weights=d.w) / (100 - np.average(d[f"{TOP}_23"], weights=d.w))
    rows.append({"party": party, "slope": b, "ci_low": lo, "ci_high": hi, "if proportional": prop})
placebo = pd.DataFrame(rows).set_index("party").sort_values("slope")
placebo["excess vs proportional"] = placebo.slope - placebo["if proportional"]
display(placebo.round(2))

# %% [markdown]
# ## 5. The places behind the numbers
# The ten places where TOP rose most, with what happened to each major party there (percentage-point swing).

# %%
cols_show = ["electorate", "total_26", "top"] + [f"{p}_swing" for p in big_other]
show = ven.sort_values("top", ascending=False).head(10)[cols_show]
show.columns = ["electorate", "votes 2026", "TOP"] + [p.replace(" Party", "").replace(" New Zealand", "") for p in big_other]
show.index = [f"{s}, {vk}"[:60] for s, vk in show.index]
display(show.round(1))

# %% [markdown]
# ## 6. How to read this
# * **Slope near −1 with a tight interval** would support "each point TOP gained cost the Greens a point". Slope near 0
#   with an interval spanning 0 means no detectable footprint at these places.
# * **The placebo table** is the check on arithmetic. Green well below its proportional benchmark, and below the other
#   parties, points at TOP's rise coinciding with Green losses specifically. If Labour looks the same, TOP's voters
#   may be coming from the same young or urban pool as both parties.
# * Four seats and a few dozen places is a small sample, and intervals are wide. Per-seat slopes especially.
# * Matching is by exact name and drops renamed or replaced places; see the coverage table.
# * A clear negative result describes places, not individual voters. Treat it as evidence for or against, then look for
#   voter-level data to confirm.
