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
# # 06 – Green Party: four North Shore seats in national context
# Party vote **and** candidate vote, 2023 → 2026, for every electorate, with `FOCUS_SEATS` highlighted.
# Ordinary votes only (`advance` + `election_day`): 2026 is preliminary with no special votes, so the figures
# are like-for-like but not final. Shares, not counts, so turnout differences don't matter.
#
# Definitions
# * **party share** = Green party votes / all valid party votes in the seat.
# * **candidate share** = the Green candidate's votes / all valid candidate votes. Only where Greens stood a
#   candidate (not-stood is missing, not zero). 2023 candidate→party comes from the staged 2023 files; 2026 from
#   `data/reference/ge2026_green_candidates.csv` (Commission's candidate list, Green candidates only).
# * **gap** = candidate share − party share (negative = Greens run a party-vote campaign there).
# * **vs national** = seat minus national, in percentage points. **Swing vs national** = seat swing − national swing.
# * **Candidate results** for the focus seats: every candidate, their party, votes and share, the winner, and where the
#   Green candidate placed (section 9). 2026 candidate parties for these four seats are in
#   `data/reference/ge2026_focus_candidates.csv` (Commission's candidate list).
# * Electorates are matched by name, renamed seats via the Commission's list; see `overlap` for boundary change.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import electorates, plotstyle, vote_scope

PARTY = "Green Party"
VOTE_SCOPE = "ordinary"    # "ordinary" (advance + election day) or "all" (adds special + overseas votes)
COUNT_STAGE = "preliminary"  # 2026 count: "preliminary" or "final" (data/raw/ge2026_final)
FOCUS_SEATS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 100)
ST = ROOT / "data/staging"

pv = electorates.align_2023(vote_scope.load("stg_party_votes", VOTE_SCOPE, COUNT_STAGE))
cv = electorates.align_2023(vote_scope.load("stg_candidate_votes", VOTE_SCOPE, COUNT_STAGE))
print(vote_scope.describe(VOTE_SCOPE, COUNT_STAGE))
cp23 = electorates.align_2023(pd.read_parquet(ST / "stg_candidate_party.parquet"))
cp26 = pd.read_csv(ROOT / "data/reference/ge2026_green_candidates.csv")
roll = pd.read_csv(ROOT / "data/reference/electorate_relationships_2026.csv").set_index("electorate_2026").roll
overlap = electorates.seat_overlap()
assert set(FOCUS_SEATS) <= set(roll.index), "unknown focus seat"

# %% [markdown]
# ## 1. Party vote share per electorate, and national

# %%
tot = pv.groupby(["election_year", "electorate"]).votes.sum().unstack(0)
grn = pv[pv.party == PARTY].groupby(["election_year", "electorate"]).votes.sum().unstack(0)
party = (grn / tot * 100).rename(columns=lambda y: f"party_{y}")
nat_party = {y: pv[(pv.election_year == y) & (pv.party == PARTY)].votes.sum() / pv[pv.election_year == y].votes.sum() * 100 for y in (2023, 2026)}
nat_party_swing = nat_party[2026] - nat_party[2023]
# The Māori electorates saw a huge Green rise, which lifts the national figure; general-roll seats are the fairer
# benchmark for the four focus seats (all general seats), so both are reported.
gen = [e for e in tot.index if e in roll.index and roll[e] == "general" or e not in roll.index]   # abolished Ōhāriu was general
gen_party = {y: grn.loc[gen, y].sum() / tot.loc[gen, y].sum() * 100 for y in (2023, 2026)}
gen_party_swing = gen_party[2026] - gen_party[2023]
print(f"General-roll seats only:               2023 {gen_party[2023]:.2f}%  2026 {gen_party[2026]:.2f}%  swing {gen_party_swing:+.2f} pts")
print(f"National {PARTY} party vote (ordinary): 2023 {nat_party[2023]:.2f}%  2026 {nat_party[2026]:.2f}%  swing {nat_party_swing:+.2f} pts")

# %% [markdown]
# ## 2. Candidate vote share where Greens stood
# `stood` is the Green candidate's electorate vote; the benchmark is pooled over seats where Greens stood in **both** years.

# %%
green_names = {
    2023: cp23[cp23.party == PARTY][["electorate", "candidate"]],
    2026: cp26,
}
rows = []
for y, names in green_names.items():
    d = cv[cv.election_year == y]
    valid = d.groupby("electorate").votes.sum()
    g = d.merge(names, on=["electorate", "candidate"]).groupby("electorate").votes.sum()
    rows.append(pd.DataFrame({"year": y, "green_votes": g, "valid": valid.reindex(g.index)}))
cand = pd.concat(rows).reset_index().pivot(index="electorate", columns="year", values=["green_votes", "valid"])
cand_share = pd.DataFrame({f"cand_{y}": cand["green_votes"][y] / cand["valid"][y] * 100 for y in (2023, 2026)})
both = cand_share.dropna().index
nat_cand = {y: cand["green_votes"][y][both].sum() / cand["valid"][y][both].sum() * 100 for y in (2023, 2026)}
nat_cand_swing = nat_cand[2026] - nat_cand[2023]
print(f"Greens stood in {cand_share.cand_2023.notna().sum()} seats in 2023, {cand_share.cand_2026.notna().sum()} in 2026, {len(both)} both years")
print(f"Green candidate vote, pooled over the {len(both)} seats contested both years: 2023 {nat_cand[2023]:.2f}%  2026 {nat_cand[2026]:.2f}%  swing {nat_cand_swing:+.2f} pts")

# %% [markdown]
# ## 3. One table, every electorate

# %%
t = party.join(cand_share, how="outer").reindex(roll.index)   # the 71 seats of 2026 (drops abolished Ōhāriu; it still counts in the national figure)
t["party_swing"] = t.party_2026 - t.party_2023
t["party_vs_nat_2023"] = t.party_2023 - nat_party[2023]
t["party_vs_nat_2026"] = t.party_2026 - nat_party[2026]
t["party_swing_vs_nat"] = t.party_swing - nat_party_swing
t["party_swing_vs_general"] = t.party_swing - gen_party_swing
t["cand_swing"] = t.cand_2026 - t.cand_2023
t["cand_swing_vs_nat"] = t.cand_swing - nat_cand_swing
t["gap_2023"] = t.cand_2023 - t.party_2023
t["gap_2026"] = t.cand_2026 - t.party_2026
# Green candidate's place among candidates, and how far behind the winner (points of the seat's candidate vote)
def placing(year):
    d = cv[cv.election_year == year].merge(green_names[year].assign(is_green=True), on=["electorate", "candidate"], how="left")
    d["is_green"] = d.is_green.fillna(False).astype(bool)
    d = d.groupby(["electorate", "candidate", "is_green"], as_index=False).votes.sum()
    d["rank"] = d.groupby("electorate").votes.rank(ascending=False, method="min")
    d["share"] = d.votes / d.groupby("electorate").votes.transform("sum") * 100
    top = d.groupby("electorate").share.max()
    g = d[d.is_green].set_index("electorate")
    return pd.DataFrame({f"cand_rank_{year}": g["rank"], f"cand_behind_winner_{year}": top.reindex(g.index) - g.share})
t = t.join(placing(2023)).join(placing(2026))
t["rank_party_2026"] = t.party_2026.rank(ascending=False).astype(int)
t["rank_party_swing"] = t.party_swing.rank(ascending=False).astype(int)
t["roll"] = roll
t["overlap"] = overlap
t["focus"] = t.index.isin(FOCUS_SEATS)
assert len(t) == 71 and t.party_2023.notna().all() and t.party_2026.notna().all()
t.round(2).to_csv(ST / "green_electorate_comparison.csv")
print(f"{len(t)} electorates -> data/staging/green_electorate_comparison.csv")

# %% [markdown]
# ## 4. The focus seats

# %%
cols = ["party_2023", "party_2026", "party_swing", "party_swing_vs_nat", "party_swing_vs_general", "rank_party_2026", "rank_party_swing", "overlap"]
display(t.loc[FOCUS_SEATS, cols].round(2))
cols = ["cand_2023", "cand_2026", "cand_swing", "cand_swing_vs_nat", "gap_2023", "gap_2026"]
display(t.loc[FOCUS_SEATS, cols].round(2))
print("Nationally: party swing", round(nat_party_swing, 2), "pts; candidate swing (matched seats)", round(nat_cand_swing, 2), "pts")
print("Party-vote swing among all 71 seats: median", round(t.party_swing.median(), 2), " range", round(t.party_swing.min(), 1), "to", round(t.party_swing.max(), 1))
print("Same four seats combined (party vote):",
      *(f"{y}: {grn.loc[FOCUS_SEATS, y].sum() / tot.loc[FOCUS_SEATS, y].sum() * 100:.2f}%  " for y in (2023, 2026)))

# %% [markdown]
# ## 5. Every seat, 2023 vs 2026
# Above the diagonal = Green share rose. Māori electorates (squares) behave very differently from general seats.

# %%
def scatter(ax, x, y, title, nat):
    for rl, marker in (("general", "o"), ("maori", "s")):
        d = t[(t.roll == rl) & ~t.focus]
        ax.scatter(d[x], d[y], s=22, marker=marker, color="#b8c4cc", label=f"{rl} (other)")
    f = t[t.focus]
    ax.scatter(f[x], f[y], s=70, color="#2a9d8f", edgecolor="black", zorder=3, label="focus")
    for name, r in f.iterrows():
        ax.annotate(name, (r[x], r[y]), xytext=(5, -3), textcoords="offset points", fontsize=8)
    lim = np.nanmax([t[x].max(), t[y].max()]) * 1.05
    ax.plot([0, lim], [0, lim], color="grey", lw=0.8, ls="--")
    ax.axvline(nat[2023], color="#c1666b", lw=0.8); ax.axhline(nat[2026], color="#c1666b", lw=0.8)
    ax.set_xlabel("2023 (%)"); ax.set_ylabel("2026 (%)"); ax.set_title(title); ax.legend(fontsize=7)

fig, axes = plt.subplots(1, 2, figsize=(13, 6))
scatter(axes[0], "party_2023", "party_2026", f"{PARTY}: party vote share (red lines = national)", nat_party)
scatter(axes[1], "cand_2023", "cand_2026", f"{PARTY}: candidate vote share (seats stood both years)", nat_cand)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 5b. Every electorate: party and candidate vote, 2023 and 2026
# Four bars per electorate, sorted by 2026 party-vote share. A missing bar means the Greens stood no candidate that
# year. Focus seats are shaded and in bold; Māori electorates are marked (M). Dashed lines are the national party share.

# %%
order = t.sort_values("party_2026").index          # barh draws bottom-up, so the largest ends up on top
bars = [("party_2023", "Party vote 2023", "#a8d5ba"), ("party_2026", "Party vote 2026", "#1b7f4b"),
        ("cand_2023", "Candidate vote 2023", "#f2c58b"), ("cand_2026", "Candidate vote 2026", "#d9731a")]
h = 0.2
fig, ax = plt.subplots(figsize=(10, 0.62 * len(order) + 2))
y = np.arange(len(order))
for i, (col, label, color) in enumerate(bars):
    ax.barh(y + (1.5 - i) * h, t.loc[order, col].values, height=h, color=color, label=label)   # 2023 above 2026 within a seat
for yi, name in zip(y, order):
    if name in FOCUS_SEATS:
        ax.axhspan(yi - 0.5, yi + 0.5, color="#fff3c4", zorder=0)
labels = [f"{n} (M)" if t.loc[n, "roll"] == "maori" else n for n in order]
ax.set_yticks(y, labels, fontsize=8)
for tick, name in zip(ax.get_yticklabels(), order):
    if name in FOCUS_SEATS:
        tick.set_fontweight("bold")
ax.axvline(nat_party[2023], color="#a8d5ba", ls="--", lw=1); ax.axvline(nat_party[2026], color="#1b7f4b", ls="--", lw=1)
ax.set_ylim(-0.6, len(order) - 0.4)
ax.set_xlabel(f"{PARTY} share of valid votes (%)")
ax.set_title(f"{PARTY}: party vote and candidate vote by electorate, 2023 vs 2026 (ordinary votes)")
ax.legend(loc="lower right"); ax.grid(axis="x", alpha=0.3)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 6. Focus seats against the national result

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=False)
for ax, kind, nat, label in ((axes[0], "party", nat_party, "Party vote"), (axes[1], "cand", nat_cand, "Candidate vote")):
    for s, marker in plotstyle.seat_markers(FOCUS_SEATS).items():   # green lines; electorates differ by marker shape
        v = [t.loc[s, f"{kind}_2023"], t.loc[s, f"{kind}_2026"]]
        if not np.isnan(v).any():
            ax.plot([2023, 2026], v, marker=marker, ms=7, color="#1b7f4b", label=s)
        else:   # no Green candidate in 2023: a single hollow marker for 2026
            ax.scatter([2026], [v[1]], marker=marker, s=50, facecolor="white", edgecolor="#1b7f4b", linewidth=1.5, zorder=3,
                       label=f"{s} (no 2023 Green candidate)")
    ax.plot([2023, 2026], [nat[2023], nat[2026]], color="black", ls="--", lw=2, label="national")
    ax.set_xticks([2023, 2026]); ax.set_ylabel("Green share (%)"); ax.set_title(label); ax.legend(fontsize=7)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 7. Is the swing local or national?
# Each bar is a seat's party-vote swing minus the national swing. Positive = Greens did better there than the country did.
# The national swing is inflated by the Māori electorates; `party_swing_vs_general` (section 4) uses general seats only.

# %%
d = t.sort_values("party_swing_vs_nat")
colors = np.where(d.focus, "#2a9d8f", "#cfd8dc")
ax = d.party_swing_vs_nat.plot.barh(figsize=(8, 14), color=colors)
ax.set_yticks(range(len(d)), d.index, fontsize=6)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Green party-vote swing minus national swing (percentage points)")
ax.set_title("Where the Green swing was bigger or smaller than national")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 7b. The same view for the candidate vote
# Candidate-vote swing minus the matched-seat national candidate swing, for seats where Greens stood both years.

# %%
d = t.dropna(subset=["cand_swing_vs_nat"]).sort_values("cand_swing_vs_nat")
colors = np.where(d.focus, "#2a9d8f", "#cfd8dc")
ax = d.cand_swing_vs_nat.plot.barh(figsize=(8, 10), color=colors)
ax.set_yticks(range(len(d)), d.index, fontsize=7)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Green candidate-vote swing minus national candidate swing (percentage points)")
ax.set_title(f"Candidate vote: {len(d)} seats contested both years")
plt.tight_layout(); plt.show()
print("Focus seats' Green candidate placing and distance behind the winner:")
display(t.loc[FOCUS_SEATS, ["cand_rank_2023", "cand_behind_winner_2023", "cand_rank_2026", "cand_behind_winner_2026"]].round(1))

# %% [markdown]
# ## 8. Candidate vote vs party vote in the focus seats
# A shrinking gap means the local candidate is closer to the party's own support.

# %%
display(t.loc[FOCUS_SEATS, ["party_2023", "cand_2023", "gap_2023", "party_2026", "cand_2026", "gap_2026"]].round(2))
g = t[t.cand_2023.notna() & t.cand_2026.notna()]
print(f"Median gap across the {len(g)} seats contested both years: 2023 {g.gap_2023.median():.2f}  2026 {g.gap_2026.median():.2f} pts")

# %% [markdown]
# ## 9. Every candidate in the focus seats
# Candidate vote, ordinary votes. `party` for 2023 comes from the staged 2023 files, for 2026 from the reference list.

# %%
focus_cp = {2023: cp23[cp23.electorate.isin(FOCUS_SEATS)][["electorate", "candidate", "party"]],
            2026: pd.read_csv(ROOT / "data/reference/ge2026_focus_candidates.csv")}
res = []
for y, names in focus_cp.items():
    d = cv[(cv.election_year == y) & cv.electorate.isin(FOCUS_SEATS)].groupby(["electorate", "candidate"], as_index=False).votes.sum()
    d = d.merge(names, on=["electorate", "candidate"], how="left")
    assert d.party.notna().all(), f"{y}: candidates without a party: {d[d.party.isna()].candidate.tolist()}"
    d["share"] = d.votes / d.groupby("electorate").votes.transform("sum") * 100
    d["rank"] = d.groupby("electorate").votes.rank(ascending=False, method="min").astype(int)
    d["year"] = y
    res.append(d)
res = pd.concat(res)
for seat in FOCUS_SEATS:
    r = res[res.electorate == seat].pivot_table(index=["party", "candidate"], columns="year", values=["votes", "share", "rank"])
    print(f"\n=== {seat} ===")
    display(res[res.electorate == seat].sort_values(["year", "votes"], ascending=[True, False])[["year", "rank", "candidate", "party", "votes", "share"]].round(1).reset_index(drop=True))

# %% [markdown]
# ### Winner and margin, 2023 → 2026

# %%
w = res[res["rank"] == 1].set_index(["electorate", "year"])
runner = res[res["rank"] == 2].set_index(["electorate", "year"])
summary = pd.DataFrame({"winner": w.candidate, "party": w.party, "share": w.share, "margin_pts": w.share - runner.share})
display(summary.round(1).unstack("year"))
