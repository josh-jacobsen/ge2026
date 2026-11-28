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
# # 15 – Every party in the focus seats, 2017 to 2026
# North Shore, Northcote, East Coast Bays and Upper Harbour. Every party that appeared on the party vote or put up a candidate,
# not just the six main parties of notebooks 08 and 10.
#
# **Data** (same table as notebooks 08 and 10, `src/focus_history.py`)
# * 2017 and 2020: seat totals pasted from the Commission's results pages (`data/reference/focus_seats_history.csv`).
# * 2023: all votes (ordinary + special + overseas). 2026: the final count, all votes (electorate totals from `out.csv`).
# * Shares are % of all valid votes of that type in the seat. Party names are merged across re-registrations (`fh.CANON`).
#
# **Read with care**
# * Upper Harbour was redrawn for 2020 and all four seats for 2026 (notebook 08, section 8), so a seat's 2017 and 2026 shares
#   are for different territory. Part of any long-run change is the boundary, not the voters.
# * Small parties are noisy: a party on 200 votes moving by 100 is a few hundredths of a point. Rank and share are shown, but
#   read only the parties with a few percent.
# * There is no national figure for 2017 and 2020 in the repo, so a party's seat result cannot be set against its national result
#   for those years (notebook 10 compares to the country for 2023 and 2026 only).
# * Candidate vote: independents appear in the 2023 and 2026 data but the 2017 and 2020 history file lists only party candidates,
#   so their shares in those two years may be slightly overstated if independents stood (section 5 prints the check).

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import focus_history as fh, plotstyle, vote_scope

VOTE_SCOPE, COUNT_STAGE = "all", "final"
SEATS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
YEARS = fh.YEARS
MIN_SHARE = 2.0      # a party gets its own chart line if it reached this share in any of the four seats and years; the rest are "Other"
PROVISIONAL_2026 = not (VOTE_SCOPE == "all" and COUNT_STAGE == "final")
COLORS = {"National Party": "#00529f", "Labour Party": "#d82c20", "Green Party": "#098137", "ACT New Zealand": "#fdb913",
          "New Zealand First Party": "#111111", "The Opportunities Party (TOP)": "#7b3f9e", "Conservative": "#5bc0eb",
          "Te Pāti Māori": "#b5121b", "New Zealand Loyal": "#8c564b", "Aotearoa Legalise Cannabis Party": "#7fb800",
          "NewZeal": "#e377c2", "Advance NZ (Umbrella party)": "#ff7f0e"}
SPARE = ["#17becf", "#bcbd22", "#aec7e8", "#ffbb78", "#c5b0d5", "#9edae5"]    # for any other party that earns a line
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 300)

# %% [markdown]
# ## 1. Load

# %%
seat, basis26 = fh.load_seat_table(SEATS, VOTE_SCOPE, COUNT_STAGE, root=ROOT)
print(vote_scope.describe(VOTE_SCOPE, COUNT_STAGE))
party = seat[seat.vote_type == "party"]
cand = seat[seat.vote_type == "candidate"]
print(f"{party.party.nunique()} parties on the party vote, {cand.party.nunique()} parties with candidates, over {YEARS}")

keys = ["electorate", "election_year"]
p_share = party.groupby(keys + ["party"]).votes.sum()
p_share = (p_share / p_share.groupby(keys).transform("sum") * 100).rename("share")
c_share = cand.groupby(keys + ["party"]).votes.sum()
c_share = (c_share / c_share.groupby(keys).transform("sum") * 100).rename("share")
assert np.allclose(p_share.groupby(keys).sum(), 100) and np.allclose(c_share.groupby(keys).sum(), 100)


def wide(share, seat_name):
    """Parties down, years across; blank = the party did not stand / was not on the ballot."""
    t = share.xs(seat_name, level="electorate").unstack("election_year").reindex(columns=YEARS)
    return t


def table(share, seat_name):
    t = wide(share, seat_name)
    t["2023→26"] = t[2026] - t[2023]
    t["2017→26"] = t[2026] - t[2017]
    return t.sort_values(2026, ascending=False, na_position="last")

# %% [markdown]
# ## 2. Party vote: every party, by seat
# % of all valid party votes. Blank = not on the ballot that year. `2023→26` and `2017→26` are changes in points (blank when a
# party is missing in either year).

# %%
for s in SEATS:
    print(f"\n{s} (party vote, %)")
    display(table(p_share, s).round(1))

# %% [markdown]
# ## 3. Party vote over time
# One panel per seat. Lines for every party that reached `MIN_SHARE`% in any seat and year; everyone else is summed into Other.
# Party colours as elsewhere. Markers are circles because each panel is one seat.

# %%
peak = p_share.groupby("party").max()
LINES = list(peak[peak >= MIN_SHARE].sort_values(ascending=False).index)
spare = iter(SPARE)
col = {p: COLORS.get(p) or next(spare) for p in LINES}
print("Lines:", LINES)
print("Parties in Other:", sorted(set(party.party) - set(LINES)))


fig, axes = plt.subplots(1, 4, figsize=(18, 5), sharey=True)
for ax, s in zip(axes, SEATS):
    for p in LINES:
        y = p_share.xs(s, level="electorate")
        y = y.xs(p, level="party").reindex(YEARS) if p in y.index.get_level_values("party") else pd.Series(np.nan, index=YEARS)
        plotstyle.trend_line(ax, YEARS, y, PROVISIONAL_2026, color=col[p], label=p, ms=4, lw=1.4)
    ax.set_title(s); ax.set_xticks(YEARS); ax.tick_params(axis="x", labelrotation=45); ax.grid(alpha=.3)
axes[0].set_ylabel("share of party vote (%)")
fig.legend([next(l for l in axes[0].lines if l.get_label() == p) for p in LINES], LINES, ncol=min(len(LINES), 6), loc="lower center", frameon=False, fontsize=8)
fig.suptitle("Party vote share by party, 2017–2026")
plt.tight_layout(rect=(0, 0.1, 1, 1)); plt.show()

# Same chart without the two big parties so the middle of the field is legible.
small = [p for p in LINES if p not in ("National Party", "Labour Party")]
fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
for ax, s in zip(axes, SEATS):
    for p in small:
        y = p_share.xs(s, level="electorate")
        y = y.xs(p, level="party").reindex(YEARS) if p in y.index.get_level_values("party") else pd.Series(np.nan, index=YEARS)
        plotstyle.trend_line(ax, YEARS, y, PROVISIONAL_2026, color=col[p], label=p, ms=4, lw=1.4)
    ax.set_title(s); ax.set_xticks(YEARS); ax.tick_params(axis="x", labelrotation=45); ax.grid(alpha=.3)
axes[0].set_ylabel("share of party vote (%)")
fig.legend([next(l for l in axes[0].lines if l.get_label() == p) for p in small], small, ncol=min(len(small), 6), loc="lower center", frameon=False, fontsize=8)
fig.suptitle("Party vote share, excluding National and Labour")
plt.tight_layout(rect=(0, 0.1, 1, 1)); plt.show()

# %% [markdown]
# ## 4. Who moved most, and where each party ranks
# Change in share, 2023 → 2026 (the last election to this one) and 2017 → 2026, across the four seats together (all four seats'
# votes pooled, so bigger seats count for more). Then each party's rank in each seat by year, among parties on the ballot.

# %%
pool = party.groupby(["election_year", "party"]).votes.sum()
pool = (pool / pool.groupby("election_year").transform("sum") * 100).unstack("election_year").reindex(columns=YEARS)
pool["2023→26"] = pool[2026] - pool[2023]
pool["2017→26"] = pool[2026] - pool[2017]
print("Four seats pooled, party vote %")
display(pool.sort_values(2026, ascending=False).head(15).round(1))
print("Gains and falls 2023→26, parties with 1%+ in either year (largest fall first)")
big = pool[(pool[[2023, 2026]].max(axis=1) >= 1)].dropna(subset=["2023→26"]).sort_values("2023→26")
display(big[[2017, 2020, 2023, 2026, "2023→26"]].round(1))

rank = p_share.groupby(keys).rank(ascending=False, method="min").astype(int).unstack("election_year").reindex(columns=YEARS)
top = pool.sort_values(2026, ascending=False).head(8).index
print("Rank in each seat (1 = most party votes), for the eight biggest parties of 2026")
display(rank.loc[(slice(None), list(top)), :].astype("Int64").unstack("electorate").swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False).reindex(columns=SEATS, level=0))

# %% [markdown]
# ## 5. Candidate vote: every party that stood
# % of all valid candidate votes, by the candidate's party. A candidate who stood in a seat in one year but not the next leaves a gap.
# Section 5 of notebook 06 and section 6 of notebook 08 cover the Greens and the winners.

# %%
for s in SEATS:
    print(f"\n{s} (candidate vote, %)")
    display(table(c_share, s).round(1))
indep = [y for y in YEARS if cand[(cand.election_year == y)].party.str.contains("ndependent", na=False).any()]
print("Years with an independent in the candidate table:", indep)

# %% [markdown]
# ## 6. Winner and runner-up, party vote leader
# Winner = most candidate votes; `margin` = winner minus runner-up as % of valid candidate votes. `party_leader` = most party votes.

# %%
ct = cand.sort_values(["election_year", "electorate", "votes"], ascending=[True, True, False])
ct["valid"] = ct.groupby(keys).votes.transform("sum")
two = ct.groupby(keys).head(2)
win = two.groupby(keys).agg(winner=("party", "first"), runner_up=("party", "last"),
                            margin=("votes", lambda v: v.iloc[0] - v.iloc[1]), valid=("valid", "first"))
win["margin_pct"] = win.margin / win.valid * 100
win["party_leader"] = party.sort_values("votes", ascending=False).groupby(keys).party.first()
win["leaders_differ"] = win.winner != win.party_leader
display(win.drop(columns="valid").round(1).unstack("election_year").swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False).reindex(SEATS, level=0))

# %% [markdown]
# ## 7. Save
# Tidy tables for a spreadsheet: one row per seat × year × party, party vote and candidate vote shares.

# %%
out = pd.concat({"party_vote_share": p_share, "candidate_vote_share": c_share}, axis=1).reset_index()
votes = pd.concat({"party_votes": party.groupby(keys + ["party"]).votes.sum(), "candidate_votes": cand.groupby(keys + ["party"]).votes.sum()}, axis=1).reset_index()
out = out.merge(votes, on=keys + ["party"], how="outer").sort_values(["electorate", "election_year", "party"])
out.round(3).to_csv(ROOT / "data/staging/focus_seats_all_parties.csv", index=False)
print("saved data/staging/focus_seats_all_parties.csv", out.shape)
