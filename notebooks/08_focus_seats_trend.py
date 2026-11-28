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
# # 08 – The four focus seats, 2017 → 2026
# North Shore, Northcote, East Coast Bays and Upper Harbour across four elections, party vote **and** candidate vote.
#
# **Data**
# * 2017 and 2020: seat totals pasted from the Commission's results pages into `data/reference/focus_seats_history.csv`
#   (final counts, special votes included). No voting-place detail, so this notebook works at seat level only.
# * 2023: staged files, **all votes** (ordinary + special + overseas) so it matches the final 2017 and 2020 figures.
# * 2026: staged files, `VOTE_SCOPE` / `COUNT_STAGE` as in the other notebooks. Currently the **final count, all votes**,
#   like-for-like with the earlier years. With the preliminary count 2026 is ordinary votes only (section 2 measures how much that matters).
#
# **Comparability**
# * Shares, not counts: turnout and enrolment differ between elections.
# * Boundaries: see section 8. In short, Upper Harbour was redrawn for 2020, and all four seats were redrawn for 2026.
# * Party names change between elections (Conservative → New Conservative → New Conservatives; Māori Party → Te Pāti Māori).
#   Section 1 prints the mapping used.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import electorates, plotstyle, vote_scope

VOTE_SCOPE = "all"      # 2026 votes counted: "ordinary" or "all" (adds special + overseas)
COUNT_STAGE = "final"  # 2026 count: "preliminary" or "final"
SEATS = ["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"]
YEARS = [2017, 2020, 2023, 2026]
MAIN = ["National Party", "Labour Party", "Green Party", "ACT New Zealand", "New Zealand First Party", "The Opportunities Party (TOP)"]
COLORS = {"National Party": "#00529f", "Labour Party": "#d82c20", "Green Party": "#098137", "ACT New Zealand": "#fdb913",
          "New Zealand First Party": "#111111", "The Opportunities Party (TOP)": "#7b3f9e", "Other": "#999999"}
SHORT = {"National Party": "National", "Labour Party": "Labour", "Green Party": "Green", "ACT New Zealand": "ACT",
         "New Zealand First Party": "NZ First", "The Opportunities Party (TOP)": "TOP", "Other": "Other"}
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)

# One name per party lineage (the Commission renamed or re-registered some parties between elections).
CANON = {
    "Conservative": "Conservative", "New Conservative": "Conservative", "New Conservatives": "Conservative",
    "Māori Party": "Te Pāti Māori", "Te Pāti Māori": "Te Pāti Māori",
    "NZ Outdoors Party": "NZ Outdoors", "NZ Outdoors & Freedom Party": "NZ Outdoors",
    "Social Credit": "Social Credit", "Democrats for Social Credit": "Social Credit",
}
canon = lambda p: CANON.get(p, p)


def trend(ax, y, marker="o", **kw):
    """Line over YEARS; the 2026 point is hollow and dashed while 2026 is ordinary votes only."""
    y = pd.Series(y).reindex(YEARS)
    prov = COUNT_STAGE != "final" or VOTE_SCOPE != "all"
    last = YEARS[-1]
    ax.plot(YEARS[:-1] if prov else YEARS, y.iloc[:-1] if prov else y, marker=marker, **kw)
    if prov:
        ax.plot(YEARS[-2:], y.iloc[-2:], ls="--", color=ax.lines[-1].get_color(), lw=1)
        ax.plot([last], [y.iloc[-1]], marker=marker, mfc="white", color=ax.lines[-1].get_color(), ls="none")

# %% [markdown]
# ## 1. Load all four elections into one table
# One row per seat × year × vote type × party. Checks below fail loudly if a seat-year is missing a vote type.

# %%
hist = pd.read_csv(ROOT / "data/reference/focus_seats_history.csv")
hist = hist[hist.electorate.isin(SEATS)]
rows = [hist.assign(basis="final").rename(columns={"party": "party_raw"})[["election_year", "electorate", "vote_type", "party_raw", "votes", "basis"]]]

ST = ROOT / "data/staging"
# 2023: every non-total row (reconciles exactly to the Commission's totals, tests/official_results/test_vote_scope_reconciles.py)
p23 = pd.read_parquet(ST / "stg_party_votes.parquet")
p23 = p23[(p23.election_year == 2023) & (p23.place_kind != "total") & p23.electorate.isin(SEATS)]
rows.append(p23.groupby(["election_year", "electorate", "party"], as_index=False).votes.sum()
            .rename(columns={"party": "party_raw"}).assign(vote_type="party", basis="final (all votes)"))
c23 = pd.read_parquet(ST / "stg_candidate_party.parquet")
c23 = c23[c23.electorate.isin(SEATS)]
rows.append(c23.rename(columns={"party": "party_raw"})[["election_year", "electorate", "party_raw", "votes"]].assign(vote_type="candidate", basis="final (all votes)"))

# 2026: scope and stage from the config; candidate parties from the Commission's candidate list
p26 = vote_scope.load("stg_party_votes", VOTE_SCOPE, COUNT_STAGE)
p26 = p26[(p26.election_year == 2026) & p26.electorate.isin(SEATS)]
basis26 = f"{COUNT_STAGE}, {VOTE_SCOPE} votes"
rows.append(p26.groupby(["election_year", "electorate", "party"], as_index=False).votes.sum()
            .rename(columns={"party": "party_raw"}).assign(vote_type="party", basis=basis26))
k26 = vote_scope.load("stg_candidate_votes", VOTE_SCOPE, COUNT_STAGE)
k26 = k26[(k26.election_year == 2026) & k26.electorate.isin(SEATS)].groupby(["election_year", "electorate", "candidate"], as_index=False).votes.sum()
cl26 = pd.read_csv(ROOT / "data/reference/ge2026_focus_candidates.csv")
k26 = k26.merge(cl26, on=["electorate", "candidate"], how="left")
assert k26.party.notna().all(), k26[k26.party.isna()]
rows.append(k26.rename(columns={"party": "party_raw"})[["election_year", "electorate", "party_raw", "votes"]].assign(vote_type="candidate", basis=basis26))

seat = pd.concat(rows, ignore_index=True)
seat["party"] = seat.party_raw.map(canon)
seat = seat.groupby(["election_year", "electorate", "vote_type", "party", "basis"], as_index=False).votes.sum()

# checks: every seat has both vote types in every year, and candidate votes are 85-100% of party votes
chk = seat.groupby(["election_year", "electorate", "vote_type"]).votes.sum().unstack()
assert len(chk) == len(SEATS) * len(YEARS), f"missing seat-years:\n{chk}"
assert chk.notna().all().all()
assert ((chk.candidate / chk.party).between(0.85, 1.0)).all(), chk
print(vote_scope.describe(VOTE_SCOPE, COUNT_STAGE))
display(chk.rename(columns={"candidate": "candidate votes", "party": "party votes"}))
changed = {k: v for k, v in CANON.items() if k != v}
print("Party names merged across years:", changed)
print("2017 rows with a source note about missing lines:", hist[hist.source.str.contains("cut off")].groupby(["election_year", "electorate"]).size().to_dict())

# %% [markdown]
# ## 2. Does leaving special votes out of 2026 matter?
# 2026 is ordinary-only until the final count, while 2017–2023 include special votes. Here is the effect for 2023, where
# both exist: each party's share of the party vote in these seats on ordinary votes only vs all votes. If the gap is
# small, the 2026 trend is trustworthy before specials arrive; if large, treat the 2026 point as provisional.

# %%
pa = pd.read_parquet(ST / "stg_party_votes.parquet")
pa = pa[(pa.election_year == 2023) & pa.electorate.isin(SEATS)]
def share(df, label):
    t = df.assign(party=df.party.map(canon)).groupby(["electorate", "party"]).votes.sum()
    return (t / t.groupby("electorate").transform("sum") * 100).rename(label)
cmp23 = pd.concat([share(pa[pa.place_kind.isin(["advance", "election_day"])], "ordinary"),
                   share(pa[pa.place_kind != "total"], "all votes")], axis=1)
cmp23["special_effect_pts"] = cmp23["all votes"] - cmp23["ordinary"]
big = cmp23.reset_index()
big = big[big.party.isin([canon(p) for p in MAIN])]
display(big.pivot(index="party", columns="electorate", values="special_effect_pts").round(2).rename(index=SHORT))
print("Positive = the party gains share once special votes are counted (2023).")

# %% [markdown]
# ## 3. Party vote share, 2017 → 2026

# %%
pt = seat[seat.vote_type == "party"].copy()
pt["valid"] = pt.groupby(["election_year", "electorate"]).votes.transform("sum")
pt["share"] = pt.votes / pt.valid * 100
pt["group"] = pt.party.where(pt.party.isin(MAIN), "Other")
grp = pt.groupby(["electorate", "election_year", "group"]).share.sum().unstack("election_year")
for s in SEATS:
    print(s)
    display(grp.loc[s].reindex(MAIN + ["Other"]).rename(index=SHORT).round(1))

fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
for ax, s in zip(axes.flat, SEATS):
    for g in MAIN:
        trend(ax, grp.loc[(s, g)], color=COLORS[g], label=SHORT[g])
    ax.set_title(s); ax.set_xticks(YEARS); ax.grid(alpha=.3)
axes[0, 0].legend(ncol=3, fontsize=8)
fig.supylabel("share of party vote (%)")
fig.suptitle(f"Party vote share (hollow 2026 point = {basis26}; earlier years final, special votes included)")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 4. Greens: party share, candidate share and the gap
# Candidate share = the Green candidate's votes / all candidate votes in the seat. **gap** = candidate − party share.

# %%
def party_candidate(party):
    p = pt[pt.party == party].set_index(["electorate", "election_year"]).share.rename("party_share")
    ct = seat[seat.vote_type == "candidate"].copy()
    ct["valid"] = ct.groupby(["election_year", "electorate"]).votes.transform("sum")
    ct["share"] = ct.votes / ct.valid * 100
    c = ct[ct.party == party].set_index(["electorate", "election_year"]).share.rename("candidate_share")
    out = pd.concat([p, c], axis=1).reindex(pd.MultiIndex.from_product([SEATS, YEARS], names=["electorate", "election_year"]))
    out["gap"] = out.candidate_share - out.party_share
    return out
green = party_candidate("Green Party")
display(green.round(1).unstack("election_year").swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False).reindex(SEATS))

# Colour means a party everywhere in these notebooks, so electorates are told apart by marker shape, not colour:
# every line is Green (the party being plotted) and each seat has its own marker.
SEAT_MARKERS = plotstyle.seat_markers(SEATS)   # circle, square, triangle, pentagon
fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
for ax, col, ttl in zip(axes, ["party_share", "candidate_share"], ["Green party vote", "Green candidate vote"]):
    for s in SEATS:
        trend(ax, green.loc[s][col], marker=SEAT_MARKERS[s], color=COLORS["Green Party"], ms=7, label=s)
    ax.set_title(ttl); ax.set_xticks(YEARS); ax.grid(alpha=.3)
axes[0].set_ylabel("share (%)")
# the legend is built from the solid lines only, so the hollow 2026 markers are not listed twice
solid = [l for l in axes[0].lines if l.get_label() in SEATS]
axes[0].legend(solid, [l.get_label() for l in solid], fontsize=8, title="Electorate")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 5. The Opportunity Party (TOP) alongside the Greens
# Background to the theory in notebook 07: does TOP's rise coincide with the Green share falling? At seat level, over
# four elections, this is only a pattern to look at, not a test.

# %%
top = party_candidate("The Opportunities Party (TOP)")
both = pd.concat({"Green party": green.party_share, "TOP party": top.party_share,
                  "Green candidate": green.candidate_share, "TOP candidate": top.candidate_share}, axis=1)
both["Green+TOP party"] = both["Green party"] + both["TOP party"]
display(both.round(1).unstack("election_year").swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False).reindex(SEATS))

fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
for ax, s in zip(axes, SEATS):
    trend(ax, both.loc[s, "Green party"], color=COLORS["Green Party"], label="Green")
    trend(ax, both.loc[s, "TOP party"], color=COLORS["The Opportunities Party (TOP)"], label="TOP")
    trend(ax, both.loc[s, "Green+TOP party"], color="#555555", label="Green + TOP")
    ax.set_title(s); ax.set_xticks(YEARS); ax.tick_params(axis="x", labelrotation=45); ax.grid(alpha=.3)
axes[0].set_ylabel("party vote share (%)"); axes[0].legend(fontsize=8)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 6. Who won each seat, and by how much
# Winner = most candidate votes. `party_leader` = most party votes. `margin_pct` = winner minus runner-up, as % of valid
# candidate votes.

# %%
ct = seat[seat.vote_type == "candidate"].sort_values(["election_year", "electorate", "votes"], ascending=[True, True, False])
ct["valid"] = ct.groupby(["election_year", "electorate"]).votes.transform("sum")
w = ct.groupby(["election_year", "electorate"]).head(2)
win = w.groupby(["election_year", "electorate"]).agg(winner=("party", "first"), runner_up=("party", "last"),
                                                     margin=("votes", lambda v: v.iloc[0] - v.iloc[1]), valid=("valid", "first"))
win["margin_pct"] = win.margin / win.valid * 100
win["party_leader"] = pt.sort_values("votes", ascending=False).groupby(["election_year", "electorate"]).party.first()
win["leaders_differ"] = win.winner != win.party_leader
display(win.drop(columns="valid").round(1).unstack("election_year").swaplevel(axis=1).sort_index(axis=1, level=0, sort_remaining=False).reindex(SEATS, level=0))

# %% [markdown]
# ## 7. National context
# Two benchmarks, both from the staged files (all 71/72 electorates' party votes added up):
# * **National** = the country's party vote. The 2023 "official" column uses all votes and equals the Commission's national
#   result (checked by `tests/official_results`). 2026 "final" is the official final result (all votes), checked against the Commission's table.
# * **General roll** = the same, leaving out the 7 Māori electorates. It is the fairer yardstick for these four general
#   seats, because the Māori seats swing very differently (Green and Te Pāti Māori surged there in 2026).
# Every swing compares like with like: **all votes in both years** once the final 2026 count is loaded (`VOTE_SCOPE="all"`,
# `COUNT_STAGE="final"`), otherwise **ordinary votes in both years**, so special votes (which lift the Greens by about 1 point
# in these seats, section 2) never distort it. For 2017 and 2020, put the Commission's national results in
# `data/reference/national_party_share_history.csv` (columns `election_year, party, share`) and they are added as columns.

# %%
roll = pd.read_csv(ROOT / "data/reference/electorate_relationships_2026.csv").set_index("electorate_2026").roll
maori = set(roll[roll == "maori"].index)
ORD = ["advance", "election_day"]
allp = pd.read_parquet(ST / "stg_party_votes.parquet")
p23_all = allp[(allp.election_year == 2023) & (allp.place_kind != "total")]
p23_ord = allp[(allp.election_year == 2023) & allp.place_kind.isin(ORD)]
p26_ord = vote_scope.load("stg_party_votes", "ordinary", "preliminary")   # ordinary-only 2026 exists for the preliminary count only
p26_ord = p26_ord[p26_ord.election_year == 2026]
p26_cfg = vote_scope.load("stg_party_votes", VOTE_SCOPE, COUNT_STAGE)
p26_cfg = p26_cfg[p26_cfg.election_year == 2026]
if COUNT_STAGE == "final" and VOTE_SCOPE == "all":     # the staged final rows must reproduce the official national shares exactly
    import etl
    nat = pd.read_csv(etl.NATIONAL_2026_FINAL)
    off = nat.assign(party=nat.party.map(etl.clean_party).map(canon)).groupby("party").party_votes.sum()
    off = off / off.sum() * 100
    got = p26_cfg.assign(party=p26_cfg.party.map(canon)).groupby("party").votes.sum()
    assert np.allclose((got / got.sum() * 100).reindex(off.index), off), "final 2026 national shares differ from the official table"

def pshare(df, general_only=False):
    if general_only:
        df = df[~df.electorate.isin(maori)]
    t = df.assign(party=df.party.map(canon)).groupby("party").votes.sum()
    return t / t.sum() * 100

LIKE = COUNT_STAGE == "final" and VOTE_SCOPE == "all"   # 2026 includes special votes, as 2023 does: compare all votes
cols = {
    "2023 official (all votes)": pshare(p23_all),
    "2023 ordinary": pshare(p23_ord),
    f"2026 {COUNT_STAGE}, {VOTE_SCOPE}": pshare(p26_cfg),
    "general roll 2023 ordinary": pshare(p23_ord, True),
    "general roll 2026 ordinary": pshare(p26_ord, True),
}
if LIKE:
    cols["general roll 2023 (all votes)"] = pshare(p23_all, True)
    cols["general roll 2026 final (all votes)"] = pshare(p26_cfg, True)
nat_file = ROOT / "data/reference/national_party_share_history.csv"
if nat_file.exists():
    h = pd.read_csv(nat_file).assign(party=lambda d: d.party.map(canon)).pivot_table(index="party", columns="election_year", values="share")
    cols = {**{f"{y} official": h[y] for y in h.columns if y < 2023}, **cols}
else:
    print("2017 and 2020 national figures not supplied (see above); showing 2023 and 2026 only")
nat_tbl = pd.DataFrame(cols).reindex([canon(p) for p in MAIN]).rename(index=SHORT)
display(nat_tbl.round(1))
# sanity: the 2023 official column must match the Commission's published national result (rows of kind "total")
chk23 = pshare(allp[(allp.election_year == 2023) & (allp.place_kind == "total")])
assert np.allclose(chk23.reindex(cols["2023 official (all votes)"].index), cols["2023 official (all votes)"]), "2023 national does not reconcile"

# Seat swing 2023 -> 2026 (ordinary votes both years) minus each benchmark's swing; negative = the seat did worse
ord23 = cmp23["all votes" if LIKE else "ordinary"].unstack("party").reindex(columns=[canon(p) for p in MAIN])
ord23.columns = MAIN
s26 = grp[2026].unstack("group")[MAIN]
seat_sw = s26 - ord23.reindex(s26.index)
def bench_sw(a, b):
    return (b - a).reindex([canon(p) for p in MAIN]).set_axis(MAIN)
b23, b26 = (p23_all, p26_cfg) if LIKE else (p23_ord, p26_ord)
nat_sw = bench_sw(pshare(b23), pshare(b26))
gen_sw = bench_sw(pshare(b23, True), pshare(b26, True))
if not LIKE and not (VOTE_SCOPE == "ordinary" and COUNT_STAGE == "preliminary"):
    print("note: seat 2026 shares follow VOTE_SCOPE/COUNT_STAGE but the benchmarks use ordinary votes; use ordinary/preliminary or all/final")
print(f"Swing 2023→2026, {'all votes (2026 final)' if LIKE else 'ordinary votes'}. The two benchmarks' own swings (points):")
display(pd.DataFrame({"national": nat_sw, "general roll": gen_sw}).rename(index=SHORT).T.round(1))
print("Seat swing minus NATIONAL swing:")
display((seat_sw - nat_sw).rename(columns=SHORT).round(1))
print("Seat swing minus GENERAL-ROLL swing (fairer for these seats):")
display((seat_sw - gen_sw).rename(columns=SHORT).round(1))

# %% [markdown]
# ## 8. Boundaries: how comparable are the years?
# The Commission redraws boundaries after each census. For these seats (from the Commission's schedules of changed and
# unchanged electorates; I could not open the PDFs from here, so please check the Upper Harbour entries):
# * 2017 → 2020: North Shore, Northcote and East Coast Bays were listed unchanged from the 2014 boundaries; **Upper Harbour was redrawn**.
# * 2020 → 2023: no review between them (the next review followed the 2023 census).
# * 2023 → 2026: **all four were redrawn** in the 2025 review (Upper Harbour gains from East Coast Bays and Wairau Valley moves to Northcote, per the proposals).
# `overlap` below measures the 2023 → 2026 change from voting places: % of each 2026 seat's election-day votes that came from
# the same-named 2023 seat's venues (100 = same area). It is a proxy, not the Commission's meshblock crosswalk.

# %%
ov = electorates.seat_overlap().reindex(SEATS).rename("overlap_2023_to_2026_pct")
era = pd.DataFrame({
    "2017→2020": ["unchanged", "unchanged", "unchanged", "REDRAWN (check)"],
    "2020→2023": ["no review"] * 4,
    "2023→2026": ["redrawn"] * 4,
}, index=SEATS)
display(era.join(ov))
print("Seat-level trends across a redraw mix real change in voters with change in who is in the seat.")

# %% [markdown]
# ## 9. Save
# The full seat × year table for a spreadsheet.

# %%
out = pt.pivot_table(index=["electorate", "party"], columns="election_year", values="share").add_prefix("party_share_")
out = out.join(green.reset_index().pivot(index="electorate", columns="election_year", values="candidate_share").add_prefix("green_cand_share_"), on="electorate")
out.round(3).to_csv(ROOT / "data/staging/focus_seats_trend.csv")
print("saved data/staging/focus_seats_trend.csv", out.shape)
