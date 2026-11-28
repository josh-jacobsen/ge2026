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
# # 13 – Campaign effort: door knocking and phone calling, 2023 vs 2026
# The four focus seats, weekly campaign-tool exports (`data/raw/campaign/<seat>_<year>_<channel>.csv`), parsed by `src/campaign.py`.
#
# **Definitions** (as the tool reports them)
# * **Attempt** = a door knocked or a call made. **Contact** = someone answered. **Meaningful interaction** = a contact the
#   volunteer logged as meaningful. Contact rate = contacts / attempts. Meaningful rate = meaningful / contacts.
# * Weeks are lined up by **weeks to election**: 0 is the week containing election day (14 Oct 2023, 7 Nov 2026, both Saturdays),
#   1 is the week before it, and so on. Rows after election week are dropped (a handful of 2023 attempts, section 1).
#
# **Read with care**
# * A week missing from an export means zero or not recorded; the files cannot say which.
# * The door-knocking exports end before election week in every seat (the last week is 1 to 2 weeks out), so door knocking
#   on the final days is not in the data. Phone exports run into election week.
# * Rates computed on a few contacts mean nothing. Cells with fewer than `MIN_CONTACTS` contacts are marked "small n".
# * The 2023 and 2026 "seats" are the same-named seats, but all four were redrawn for 2026 (notebook 08, section 8), and
#   the campaign's own definition of its seat area is not known. We also do not know that the tool, the definition of an
#   attempt or meaningful interaction, or the volunteer base stayed the same.
# * Four seats and two elections cannot show that effort changed the result. Section 5 sets effort beside the results to
#   describe them together; it is not a test.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import campaign, focus_history as fh, plotstyle

SEATS = list(campaign.SEATS.values())
MIN_CONTACTS = 100          # below this a rate is marked "small n"
VOTE_SCOPE, COUNT_STAGE = "all", "final"   # results shown in section 5, as in notebooks 08 and 10
CH = {"door_knocking": "Door knocking", "phone_calls": "Phone calls"}
YEAR_STYLE = {2023: dict(color="#8a8a8a", label="2023"), 2026: dict(color="#1d1d1d", label="2026")}   # neutral: colour means a party elsewhere
MARK = plotstyle.seat_markers(SEATS)
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)

# %% [markdown]
# ## 1. Load and check
# `campaign.load_all` checks each export (contacts never above attempts, rates equal the counts, Monday-to-Sunday ISO weeks,
# weeks inside the file's year) and fails loudly if any of the 16 seat × year × channel files is missing.

# %%
full = campaign.load_all(through_election=False)
eff = campaign.load_all()
after = full[full.weeks_to_election < 0]
print(f"{full.groupby(['seat','year','channel']).ngroups} exports, {len(full)} weekly rows, {full.attempts.sum():,} attempts")
print(f"dropped as after election week: {len(after)} rows, {after.attempts.sum()} attempts")
display(after.groupby(["seat", "year", "channel"])[["attempts", "contacts"]].sum())

# %% [markdown]
# ## 2. How much effort, by seat, year and channel
# Attempts, contacts and the two rates, through election week.

# %%
tot = campaign.summarize(eff, ["seat", "year", "channel"])
tot["note"] = np.where(tot.contacts < MIN_CONTACTS, "small n", "")
att = tot.attempts.unstack(["year", "channel"]).reindex(SEATS)
att[("all", "2023")] = att[2023].sum(axis=1)
att[("all", "2026")] = att[2026].sum(axis=1)
att.loc["Four seats"] = att.sum()
print("Attempts")
display(att)
rates = tot.reset_index().pivot(index="seat", columns=["year", "channel"], values=["contact_rate", "meaningful_rate"])
print("Contact rate (contacts / attempts) and meaningful rate (meaningful / contacts), %. Door knocking 2023 rests on very few contacts per seat (see the contacts table below).")
display((rates * 100).round(1).reindex(SEATS))
print("Contacts behind each rate")
display(tot.contacts.unstack(["year", "channel"]).reindex(SEATS))

# %% [markdown]
# ## 3. When the effort happened
# Weekly attempts against weeks to election (left = early in the campaign, right = election week), and the cumulative share of
# the campaign's attempts. Most phone effort lands in the final six weeks in both years; door knocking in 2026 comes in bursts.

# %%
LAST = int(eff.weeks_to_election.max())
weeks = pd.RangeIndex(LAST, -1, -1, name="weeks_to_election")


def by_week(seat, year, channel):
    d = eff[(eff.seat == seat) & (eff.year == year) & (eff.channel == channel)].groupby("weeks_to_election").attempts.sum()
    return d.reindex(weeks, fill_value=0)


fig, axes = plt.subplots(2, 4, figsize=(16, 6.5), sharex=True)
for r, ch in enumerate(CH):
    for c, s in enumerate(SEATS):
        ax = axes[r, c]
        for y in (2023, 2026):
            ax.plot(weeks, by_week(s, y, ch), marker=MARK[s], ms=4, lw=1.2, **YEAR_STYLE[y])
        ax.set_title(f"{s}: {CH[ch].lower()}", fontsize=10); ax.grid(alpha=.3)
        ax.set_xlim(LAST + 1, -1)
axes[0, 0].legend(); axes[0, 0].set_ylabel("attempts per week"); axes[1, 0].set_ylabel("attempts per week")
for ax in axes[1]:
    ax.set_xlabel("weeks to election (0 = election week)")
plt.tight_layout(); plt.show()

fig, axes = plt.subplots(2, 4, figsize=(16, 6), sharex=True, sharey=True)
for r, ch in enumerate(CH):
    for c, s in enumerate(SEATS):
        ax = axes[r, c]
        for y in (2023, 2026):
            w = by_week(s, y, ch)
            ax.plot(weeks, w.cumsum() / w.sum() * 100, marker=MARK[s], ms=3, lw=1.2, **YEAR_STYLE[y])
        ax.set_title(f"{s}: {CH[ch].lower()}", fontsize=10); ax.grid(alpha=.3); ax.set_xlim(LAST + 1, -1)
axes[0, 0].legend(); axes[0, 0].set_ylabel("cumulative % of attempts"); axes[1, 0].set_ylabel("cumulative % of attempts")
for ax in axes[1]:
    ax.set_xlabel("weeks to election (0 = election week)")
plt.tight_layout(); plt.show()

# share of each year's attempts in the last 6 weeks (weeks 0 to 5), and in election week alone
last6 = eff[eff.weeks_to_election <= 5].groupby(["seat", "year", "channel"]).attempts.sum() / tot.attempts * 100
ew = eff[eff.weeks_to_election == 0].groupby(["seat", "year", "channel"]).attempts.sum().reindex(tot.index, fill_value=0) / tot.attempts * 100
print("% of attempts in the last 6 weeks (weeks to election 0 to 5)")
display(last6.unstack(["year", "channel"]).reindex(SEATS).round(0))
print("% of attempts in election week itself (0 for door knocking: those exports end before it)")
display(ew.unstack(["year", "channel"]).reindex(SEATS).round(0))

# %% [markdown]
# ## 4. Contact and meaningful rates over the campaign
# Rates by weeks-to-election band. Early weeks have few attempts so their rates swing; the late bands carry most of the volume.
# Cells under `MIN_CONTACTS` contacts are blank.

# %%
BANDS = pd.cut(eff.weeks_to_election, [-1, 0, 2, 5, 11, 100], labels=["0 (election wk)", "1-2", "3-5", "6-11", "12+"])
band = campaign.summarize(eff.assign(band=BANDS, year=eff.year), ["channel", "year", "band"])
band = band[band.attempts > 0]
for ch in CH:
    b = band.loc[ch]
    keep = b.contacts >= MIN_CONTACTS
    show = pd.concat({"attempts": b.attempts, "contact %": (b.contact_rate * 100).where(keep).round(1),
                      "meaningful %": (b.meaningful_rate * 100).where(keep).round(1)}, axis=1)
    print(f"{CH[ch]}, all four seats together (blank = under {MIN_CONTACTS} contacts)")
    display(show.unstack("year").swaplevel(axis=1).sort_index(axis=1, level=0))

phone = eff[eff.channel == "phone_calls"]
fig, axes = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
for ax, s in zip(axes, SEATS):
    for y in (2023, 2026):
        d = phone[(phone.seat == s) & (phone.year == y)].groupby("weeks_to_election")[["attempts", "contacts"]].sum()
        d = d[d.contacts >= 20]                       # a rate on fewer than 20 contacts is noise
        ax.plot(d.index, d.contacts / d.attempts * 100, marker=MARK[s], ms=4, lw=1.2, **YEAR_STYLE[y])
    ax.set_title(s, fontsize=10); ax.grid(alpha=.3); ax.set_xlim(LAST + 1, -1)
    ax.set_xlabel("weeks to election")
axes[0].set_ylabel("phone contact rate (%)"); axes[0].legend()
fig.suptitle("Phone contact rate by week (weeks with 20+ contacts)")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 5. Effort beside the results
# Effort per 1,000 party votes cast in the seat (so a bigger seat does not look busier), next to the Green party vote share and
# the left-minus-right lead from notebooks 08 and 10 (all votes both years, 2026 final). The seat result tables use each year's
# own boundaries. **This describes the four seats together; it does not show that effort moved a result.**
# With four seats the pattern in the table can be read directly, and any statistic computed from it would be meaningless.

# %%
seat_tbl, basis26 = fh.load_seat_table(SEATS, VOTE_SCOPE, COUNT_STAGE, root=ROOT)
party_b = fh.bloc_shares(seat_tbl, "party")
pv = seat_tbl[seat_tbl.vote_type == "party"].groupby(["electorate", "election_year"]).votes.sum()
green = (seat_tbl[(seat_tbl.vote_type == "party") & (seat_tbl.party == "Green Party")]
         .set_index(["electorate", "election_year"]).votes / pv * 100)
res = pd.DataFrame({
    "Green % 2023": green.xs(2023, level=1), "Green % 2026": green.xs(2026, level=1),
    "lead 2023": party_b["lead (Left - Right)"].xs(2023, level=1), "lead 2026": party_b["lead (Left - Right)"].xs(2026, level=1),
}).reindex(SEATS)
res["Green change"] = res["Green % 2026"] - res["Green % 2023"]
res["lead change"] = res["lead 2026"] - res["lead 2023"]
per1000 = eff.groupby(["seat", "year"]).attempts.sum().unstack("year")
for y in (2023, 2026):
    per1000[f"attempts per 1,000 party votes {y}"] = per1000[y] / pv.xs(y, level=1).reindex(per1000.index) * 1000
per1000["total attempts 2023"], per1000["total attempts 2026"] = per1000[2023], per1000[2026]
per1000["effort multiple"] = per1000[2026] / per1000[2023]
out = per1000.drop(columns=[2023, 2026]).reindex(SEATS).join(res)
display(out.round(1))
print(f"basis for results: {basis26}")

# %% [markdown]
# ## 6. Save
# One tidy weekly table (through election week) for a spreadsheet.

# %%
eff.sort_values(["seat", "year", "channel", "weeks_to_election"], ascending=[True, True, True, False]).to_csv(
    ROOT / "data/staging/campaign_effort.csv", index=False)
print("saved data/staging/campaign_effort.csv", eff.shape)
