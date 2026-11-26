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
# # 11 – Top 3 voting places per electorate: Green Party and Opportunity Party (TOP)
# A **voting place is the whole venue**: its votes are added up over every electorate that lists it (so Milford Shopping Centre
# is one place with all its voters, the same as the swing map in notebook 04). Each venue belongs to its **home electorate**,
# the general-roll electorate with the most votes there. For each home electorate, party vote, 2023 and 2026:
# * **Top 3 by number of votes** for the party.
# * **Top 3 by share** of all ballots cast at the venue, among venues with at least `MIN_VOTES` valid party votes.
# * **`home %`** = the share of the party's votes at the venue that came from voters of the home electorate. Low means the
#   venue draws voters from elsewhere (a CBD hall, a mall on an electorate edge); the electorate notebooks (05–07) are the
#   place for questions about an electorate's own voters.
#
# **Read with care**
# * Counts follow where people are: the biggest venues (malls, halls) have the most votes of everything. Share shows where the
#   party is relatively strongest.
# * A tiny venue can post a huge share from a handful of votes, hence `MIN_VOTES`.
# * 2026 is preliminary, ordinary votes only: special, overseas and mobile-team votes belong to an electorate, not a venue.
# * Home electorate is chosen separately for each election, and electorates were redrawn for 2026, so a venue can change
#   electorate between years and the 2023 and 2026 lists need not match.
# * Māori-roll voters at a venue count in its totals but never decide its home electorate.
# * Where an electorate has fewer than 3 qualifying venues, it simply lists fewer.
# * Votes cast at a venue say where people voted, not where they live.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import booths, vote_scope

COUNT_STAGE = "preliminary"   # 2026 count: "preliminary" or "final"
MIN_VOTES = 100               # minimum valid ballots at a venue to be ranked by share
TOP_N = 3
FOCUS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
PARTIES = {"green": "Green Party", "top": "Opportunity Party (TOP)"}
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 400, "display.max_colwidth", 70)

# %% [markdown]
# ## 1. One row per venue
# `booths.venue_table` sums each venue over all electorates and records the votes from home-electorate voters.

# %%
pv = vote_scope.load("stg_party_votes", "ordinary", COUNT_STAGE)
print(vote_scope.describe("ordinary", COUNT_STAGE))
vt = booths.venue_table(pv)
print(vt.groupby("election_year").agg(venues=("total", "size"), electorates=("home_electorate", "nunique")))
# venue totals should equal the ordinary-vote total, except venues listed only under Māori electorates (no home electorate)
lost = pv.groupby("election_year").votes.sum() - vt.groupby("election_year").total.sum()
print("ordinary votes not in any venue row (no general-roll home electorate):", lost.to_dict())
assert (lost >= 0).all() and (lost / pv.groupby("election_year").votes.sum() < 0.001).all()
m = vt[(vt.election_year == 2026) & vt.place.str.contains("Milford Shopping")]
display(m[["place", "home_electorate", "n_electorates", "total", "home_total", "green", "green_home", "top", "top_home"]])

# %% [markdown]
# ## 2. Top 3 per home electorate

# %%
tables = {(p, by): booths.top_n(vt, p, by, MIN_VOTES if by == "pct" else 0, TOP_N) for p in PARTIES for by in ("votes", "pct")}

def view(t, party):
    t = t.rename(columns={party: "party votes", "pct": "% of venue", "home_pct": "home %", "total": "venue ballots", "n_electorates": "electorates listing"})
    return t[["election_year", "home_electorate", "rank", "place", "party votes", "% of venue", "home %", "venue ballots", "electorates listing"]].round(1)

def show_focus(party):
    for year in (2023, 2026):
        for seat in FOCUS:
            for by, title in (("votes", "most votes"), ("pct", f"highest share (min {MIN_VOTES} ballots)")):
                t = view(tables[party, by], party)
                t = t[(t.election_year == year) & (t.home_electorate == seat)].drop(columns=["election_year", "home_electorate"])
                print(f"\n{PARTIES[party]} | {seat} | {year} | {title}")
                display(t.set_index("rank"))

show_focus("green")

# %%
show_focus("top")

# %% [markdown]
# ## 3. Do the same venues keep topping the list?
# Of the 2026 top 3 in each focus electorate, how many were also top 3 in 2023 (same venue)?

# %%
rows = []
for (party, by), t in tables.items():
    for seat in FOCUS:
        a = set(t[(t.election_year == 2023) & (t.home_electorate == seat)].venue_id)
        b = set(t[(t.election_year == 2026) & (t.home_electorate == seat)].venue_id)
        rows.append({"party": PARTIES[party], "ranked by": by, "electorate": seat, "in both years": len(a & b)})
display(pd.DataFrame(rows).pivot_table(index=["party", "ranked by"], columns="electorate", values="in both years").reindex(columns=FOCUS))

# %% [markdown]
# ## 4. Every electorate
# All home electorates, both parties, both rankings, saved for a spreadsheet: `data/staging/top_booths.csv` (gitignored).
# Notebook 12 turns the same venues into a web page.

# %%
out = pd.concat([view(t, p).assign(party=PARTIES[p], ranked_by=by) for (p, by), t in tables.items()], ignore_index=True)
out.to_csv(ROOT / "data" / "staging" / "top_booths.csv", index=False)
print(out.groupby(["party", "ranked_by", "election_year"]).home_electorate.nunique().unstack())
for p in PARTIES:
    print(f"\n{PARTIES[p]}: ten highest-share venues, 2026")
    display(view(tables[p, "pct"], p).query("election_year == 2026 and rank == 1").sort_values("% of venue", ascending=False).head(10).drop(columns="rank"))
