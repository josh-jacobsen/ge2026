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
# # 10 – Left bloc vs right bloc in the four focus seats, 2017 → 2026
# * **Left bloc** = Labour + Green + The Opportunities Party (TOP). **Right bloc** = National + ACT + NZ First.
#   (This is the grouping as given; TOP describes itself as neither, so section 3 also shows the left bloc without it.)
# * Every other party (Te Pāti Māori, Conservative, minor parties) is **Other**.
# * Seats: North Shore, Northcote, East Coast Bays, Upper Harbour. Elections: 2017, 2020, 2023, 2026.
# * Shares are of **all valid votes** in the seat. `of two-bloc` shares ignore Other, so a minor party that came and went
#   (New Conservative in 2020, say) does not move the picture.
# * Both the **party vote** and the **candidate vote** (each candidate counted for their party).
#
# **Read with care**
# * 2026 follows `VOTE_SCOPE` / `COUNT_STAGE`: currently the **final count, all votes** (solid points). With the preliminary
#   ordinary-only count the 2026 points are hollow, and section 6 measures what leaving special votes out does to the blocs.
#   Sections 5 and 7 compare **ordinary votes** in both years (the only basis with voting-place detail) using the preliminary count;
#   section 7 also has the all-votes comparison against the official final result.
# * Boundaries changed (section 8): Upper Harbour was redrawn for 2020, and all four seats for 2026.
# * Bloc colours are deliberately not party colours: teal = left bloc, orange = right bloc.
# * Seat-level shares over four elections describe what happened; they do not explain why.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import electorates, focus_history as fh, plotstyle, vote_scope

VOTE_SCOPE = "all"      # 2026 votes counted: "ordinary" or "all" (adds special + overseas)
COUNT_STAGE = "final"  # 2026 count: "preliminary" or "final"
SEATS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
YEARS = fh.YEARS
PROVISIONAL_2026 = not (VOTE_SCOPE == "all" and COUNT_STAGE == "final")
LEFT_C, RIGHT_C = "#2a9d8f", "#e76f51"           # bloc colours, not party colours
LEFT, RIGHT = "Left", "Right"
MARK = plotstyle.seat_markers(SEATS)
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)

# %% [markdown]
# ## 1. Load
# Same data as notebook 08 (`src/focus_history.py`): 2017 and 2020 from `data/reference/focus_seats_history.csv`,
# 2023 with all votes, 2026 per the settings above.

# %%
seat, basis26 = fh.load_seat_table(SEATS, VOTE_SCOPE, COUNT_STAGE)
print(vote_scope.describe(VOTE_SCOPE, COUNT_STAGE))
print("Bloc members:", fh.BLOCS)
party_b = fh.bloc_shares(seat, "party")
cand_b = fh.bloc_shares(seat, "candidate")
assert len(party_b) == len(SEATS) * len(YEARS)
assert np.allclose(party_b[[LEFT, RIGHT, "Other"]].sum(axis=1), 100)

def show(b, cols, title):
    print(title)
    t = b[cols].unstack("election_year").swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False)
    display(t.reindex(SEATS).round(1))

# %% [markdown]
# ## 2. Party vote: left vs right
# `lead` = left share minus right share (positive = the left bloc is ahead in the seat).

# %%
show(party_b, [LEFT, RIGHT, "Other", "lead (Left - Right)", "Left of two-bloc"], "Party vote, % of all valid votes")

fig, axes = plt.subplots(1, 4, figsize=(15, 3.8), sharey=True)
for ax, s in zip(axes, SEATS):
    d = party_b.loc[s]
    plotstyle.trend_line(ax, YEARS, d[LEFT].reindex(YEARS), PROVISIONAL_2026, color=LEFT_C, label="Left bloc", ms=7)
    plotstyle.trend_line(ax, YEARS, d[RIGHT].reindex(YEARS), PROVISIONAL_2026, color=RIGHT_C, label="Right bloc", ms=7)
    ax.axhline(50, color="grey", lw=.6, ls=":")
    ax.set_title(s); ax.set_xticks(YEARS); ax.tick_params(axis="x", labelrotation=45); ax.grid(alpha=.3)
axes[0].set_ylabel("share of party vote (%)")
handles = [l for l in axes[0].lines if l.get_label() in ("Left bloc", "Right bloc")]
axes[0].legend(handles, [h.get_label() for h in handles], fontsize=8)
fig.suptitle(f"Party vote by bloc (hollow 2026 = {basis26}; dotted line = 50%)")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 3. Is the left bloc's rise really about TOP?
# TOP went from about 2% to 6–9% of the party vote. Here is the left bloc with and without it (Labour + Green only), and
# TOP's own share, so you can see how much of any left-bloc change is TOP.

# %%
d = party_b.copy()
tab = pd.concat({
    "TOP": seat[(seat.vote_type == "party") & (seat.party == "The Opportunities Party (TOP)")].set_index(["electorate", "election_year"]).votes
           / seat[seat.vote_type == "party"].groupby(["electorate", "election_year"]).votes.sum() * 100,
}, axis=1)
tab["Left incl. TOP"] = d[LEFT]
tab["Left excl. TOP (Labour+Green)"] = d[LEFT] - tab["TOP"]
tab["Right"] = d[RIGHT]
tab["lead incl. TOP"] = d[LEFT] - d[RIGHT]
tab["lead excl. TOP"] = tab["Left excl. TOP (Labour+Green)"] - d[RIGHT]
display(tab.round(1).unstack("election_year").swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False).reindex(SEATS))

# %% [markdown]
# ## 4. Left lead in all four seats
# One line per seat (marker shape tells them apart). Above zero the left bloc is ahead; below zero the right is.

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), sharey=True)
for ax, b, ttl in zip(axes, (party_b, cand_b), ("Party vote", "Candidate vote")):
    for s in SEATS:
        plotstyle.trend_line(ax, YEARS, b.loc[s, "lead (Left - Right)"].reindex(YEARS), PROVISIONAL_2026,
                             marker=MARK[s], color="#444444", ms=7, label=s)
    ax.axhline(0, color="black", lw=.8)
    ax.set_title(f"{ttl}: left share minus right share (points)"); ax.set_xticks(YEARS); ax.grid(alpha=.3)
axes[0].set_ylabel("points")
solid = [l for l in axes[0].lines if l.get_label() in SEATS]
axes[0].legend(solid, [l.get_label() for l in solid], fontsize=8, title="Electorate")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 5. Which parties moved the blocs, 2023 → 2026
# Change in each party's share of the party vote (ordinary votes in both years, so special votes do not distort it).

# %%
pv = vote_scope.load("stg_party_votes", "ordinary", "preliminary")   # ordinary-only 2026 exists for the preliminary count only
pv = pv[pv.electorate.isin(SEATS)]
pv = pv[pv.election_year.isin([2023, 2026])]
# 2023 here is also ordinary-only (vote_scope.load returns 2023 ordinary rows for scope "ordinary")
six = fh.BLOCS[LEFT] + fh.BLOCS[RIGHT]
sh = pv.groupby(["electorate", "election_year", "party"]).votes.sum()
sh = (sh / sh.groupby(["electorate", "election_year"]).transform("sum") * 100).unstack("election_year")
move = (sh[2026].fillna(0) - sh[2023].fillna(0)).unstack("party").reindex(columns=six)
move.columns = [c.replace("The Opportunities Party (TOP)", "TOP").replace(" Party", "").replace(" New Zealand", "").replace("New Zealand First", "NZ First")
                for c in move.columns]
move["Left bloc"] = move[["Labour", "Green", "TOP"]].sum(axis=1)
move["Right bloc"] = move[["National", "ACT", "NZ First"]].sum(axis=1)
display(move.reindex(SEATS).round(1))

# %% [markdown]
# ## 6. How much does leaving special votes out of 2026 matter?
# 2023 both ways, same seats: bloc shares on ordinary votes vs all votes. A positive number means the bloc gains share once
# special votes are counted. Expect the same direction in 2026 when they arrive (only a guide: 2026 turnout may differ).

# %%
allp = pd.read_parquet(ROOT / "data/staging/stg_party_votes.parquet")
allp = allp[(allp.election_year == 2023) & allp.electorate.isin(SEATS)].assign(vote_type="party")
allp["party"] = allp.party.map(fh.canon)
def blocs_for(df):
    return fh.bloc_shares(df.groupby(["election_year", "electorate", "vote_type", "party"], as_index=False).votes.sum(), "party")
eff = (blocs_for(allp[allp.place_kind != "total"]) - blocs_for(allp[allp.place_kind.isin(["advance", "election_day"])]))
display(eff.xs(2023, level="election_year")[[LEFT, RIGHT, "lead (Left - Right)"]].reindex(SEATS).round(2)
        .rename(columns={LEFT: "Left", RIGHT: "Right", "lead (Left - Right)": "lead"}))

# %% [markdown]
# ## 7. Against the country
# The same blocs for the whole country (all electorates' party votes added), and for the general roll only (the 7 Māori
# electorates left out: the fairer yardstick for these general seats). 2023 official = all votes (matches the Commission);
# the other columns are ordinary votes. 2017 and 2020 national figures are not in the repo, so the comparison is 2023 → 2026.

# %%
roll = pd.read_csv(ROOT / "data/reference/electorate_relationships_2026.csv").set_index("electorate_2026").roll
maori = set(roll[roll == "maori"].index)
ORD = ["advance", "election_day"]
raw = pd.read_parquet(ROOT / "data/staging/stg_party_votes.parquet")
raw26 = vote_scope.load("stg_party_votes", "ordinary", "preliminary")

def nat_blocs(df, general_only=False):
    if general_only:
        df = df[~df.electorate.isin(maori)]
    t = df.assign(party=df.party.map(fh.canon), electorate="national", vote_type="party").groupby(["election_year", "electorate", "vote_type", "party"], as_index=False).votes.sum()
    return fh.bloc_shares(t, "party").iloc[0]

cols = {
    "2023 official (all votes)": nat_blocs(raw[(raw.election_year == 2023) & (raw.place_kind != "total")]),
    "2023 ordinary": nat_blocs(raw[(raw.election_year == 2023) & raw.place_kind.isin(ORD)]),
    "2026 ordinary": nat_blocs(raw26[raw26.election_year == 2026]),
    "general roll 2023 ordinary": nat_blocs(raw[(raw.election_year == 2023) & raw.place_kind.isin(ORD)], True),
    "general roll 2026 ordinary": nat_blocs(raw26[raw26.election_year == 2026], True),
}
nat_tbl = pd.DataFrame(cols).loc[[LEFT, RIGHT, "Other", "lead (Left - Right)"]]
display(nat_tbl.round(1))

# Seat lead swing 2023 -> 2026 (ordinary both years) minus each benchmark's lead swing: positive = the seat moved further
# to the left than the benchmark did.
seat_ord = pd.concat([blocs_for(allp[allp.place_kind.isin(ORD)])["lead (Left - Right)"].xs(2023, level="election_year").rename(2023)], axis=1)
p26 = raw26[(raw26.election_year == 2026) & raw26.electorate.isin(SEATS)].assign(vote_type="party")
p26["party"] = p26.party.map(fh.canon)
seat_ord[2026] = blocs_for(p26)["lead (Left - Right)"].xs(2026, level="election_year")
seat_ord["seat swing in lead"] = seat_ord[2026] - seat_ord[2023]
seat_ord["national lead swing"] = nat_tbl.loc["lead (Left - Right)", "2026 ordinary"] - nat_tbl.loc["lead (Left - Right)", "2023 ordinary"]
seat_ord["general-roll lead swing"] = nat_tbl.loc["lead (Left - Right)", "general roll 2026 ordinary"] - nat_tbl.loc["lead (Left - Right)", "general roll 2023 ordinary"]
seat_ord["vs national"] = seat_ord["seat swing in lead"] - seat_ord["national lead swing"]
seat_ord["vs general roll"] = seat_ord["seat swing in lead"] - seat_ord["general-roll lead swing"]
display(seat_ord.reindex(SEATS).round(1))

# %% [markdown]
# **Like-for-like with the final count.** When `VOTE_SCOPE="all"` and `COUNT_STAGE="final"`, 2026 includes special votes just as
# the official 2023 figures do, so the comparison below is all votes in both years (no ordinary-only caveat).

# %%
if VOTE_SCOPE == "all" and COUNT_STAGE == "final":
    all26 = vote_scope.load("stg_party_votes", "all", "final")
    all26 = all26[all26.election_year == 2026]
    cols_f = {
        "2023 official (all votes)": nat_tbl["2023 official (all votes)"],
        "2026 official (final)": nat_blocs(all26),
        "general roll 2023 (all votes)": nat_blocs(raw[(raw.election_year == 2023) & (raw.place_kind != "total")], True),
        "general roll 2026 (final)": nat_blocs(all26, True),
    }
    nat_f = pd.DataFrame(cols_f).loc[[LEFT, RIGHT, "Other", "lead (Left - Right)"]]
    display(nat_f.round(1))
    lead = party_b["lead (Left - Right)"].unstack("election_year")
    seat_f = pd.DataFrame({2023: lead[2023], 2026: lead[2026]})
    seat_f["seat swing in lead"] = seat_f[2026] - seat_f[2023]
    seat_f["national lead swing"] = nat_f.loc["lead (Left - Right)", "2026 official (final)"] - nat_f.loc["lead (Left - Right)", "2023 official (all votes)"]
    seat_f["general-roll lead swing"] = nat_f.loc["lead (Left - Right)", "general roll 2026 (final)"] - nat_f.loc["lead (Left - Right)", "general roll 2023 (all votes)"]
    seat_f["vs national"] = seat_f["seat swing in lead"] - seat_f["national lead swing"]
    seat_f["vs general roll"] = seat_f["seat swing in lead"] - seat_f["general-roll lead swing"]
    display(seat_f.reindex(SEATS).round(1))
else:
    print("final count not selected: skipped")

# %% [markdown]
# ## 8. Boundaries
# From the Commission's schedules (I could not open the PDFs from here, so please check the Upper Harbour entries):
# * 2017 → 2020: North Shore, Northcote and East Coast Bays unchanged; **Upper Harbour redrawn**.
# * 2020 → 2023: no review.
# * 2023 → 2026: **all four redrawn**. `overlap` is the share of each 2026 seat's election-day votes from the same-named 2023 seat's venues.

# %%
display(pd.DataFrame({"2017→2020": ["unchanged", "unchanged", "unchanged", "REDRAWN (check)"], "2020→2023": ["no review"] * 4,
                      "2023→2026": ["redrawn"] * 4}, index=SEATS).join(electorates.seat_overlap().reindex(SEATS).rename("overlap 2023→2026 %")))

# %% [markdown]
# ## 9. Save

# %%
out = pd.concat({"party": party_b, "candidate": cand_b}, names=["vote_type"]).reset_index()
out.round(3).to_csv(ROOT / "data/staging/blocs_focus_seats.csv", index=False)
print("saved data/staging/blocs_focus_seats.csv", out.shape)
