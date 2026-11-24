# %% [markdown]
# # 04 – 2026 vs 2023 analysis
# Like-for-like: **ordinary votes only** (`advance` + `election_day`), because 2026 is preliminary and has no
# special votes. Change `FOCUS` to look at any party.
#
# Two ways to compare, because the 2025 boundary review changed the electorates:
# * **Electorate level**: matched by name, with the Commission's 2025 rename list for the 10 renamed seats (boundaries of many moved).
# * **Voting-place level**: venues are summed across every electorate that lists them, then 2026 venues are paired
#   with 2023 venues **by geocoded distance** (≤ `MATCH_M`, mutual nearest neighbour). This works for any seat.
#
# Needs notebook 03 (geocoding) to have run; venues without coordinates are left off the maps.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd, folium
import matplotlib.pyplot as plt
from branca.colormap import LinearColormap
import places, maps

ST = ROOT / "data/staging"
FOCUS = "Green Party"
MIN_VOTES = 100        # ignore tiny venues: shares are noisy (and < 6 votes are zeroed by the Commission)
MATCH_M = 300          # max distance between a 2023 and a 2026 venue to call them the same place
BBOX = None            # e.g. (-37.2, -36.5, 174.3, 175.1) = (lat_min, lat_max, lon_min, lon_max) to zoom the maps
pd.set_option("display.width", 200, "display.max_columns", 30)

pv = pd.read_parquet(ST / "stg_party_votes.parquet")
pv = pv[pv.place_kind.isin(places.ORDINARY)]
geo = pd.read_csv(ROOT / "data/geo/geocode_cache.csv")
rel = pd.read_csv(ROOT / "data/reference/electorate_relationships_2026.csv")

# %% [markdown]
# ## 1. Party vote share by electorate (matched by name; see the Commission's rename list)

# %%
def share(df, by):
    t = df.groupby(by + ["party"])["votes"].sum().reset_index()
    t["share"] = t.votes / t.groupby(by)["votes"].transform("sum") * 100
    return t

import electorates
pv_named = electorates.align_2023(pv)   # 2023 rows of the 10 renamed seats get their 2026 name (Commission's list)
names = pv_named.groupby("election_year").electorate.agg(set)
comparable = names[2023] & names[2026]
by_elec = share(pv_named[pv_named.electorate.isin(comparable)], ["election_year", "electorate"])
wide = by_elec.pivot_table(index=["electorate", "party"], columns="election_year", values="share")
wide["swing_pts"] = wide[2026] - wide[2023]
print(f"{len(comparable)} of {len(rel)} electorates compared across years (by name, renames via the Commission list)")
focus_swing = wide.xs(FOCUS, level="party").dropna().sort_values("swing_pts")
display(focus_swing.round(2).head(5)); display(focus_swing.round(2).tail(5))

# %% [markdown]
# ## 2. National swing by party (all ordinary votes)

# %%
tot = share(pv, ["election_year"]).pivot(index="party", columns="election_year", values="share")
tot["swing_pts"] = tot[2026] - tot[2023]
tot = tot[tot[[2023, 2026]].max(axis=1) >= 0.5].sort_values("swing_pts")   # drop micro-parties for readability
ax = tot["swing_pts"].plot.barh(figsize=(8, 6), color=np.where(tot["swing_pts"] > 0, "#2a9d8f", "#c1666b"))
ax.set_xlabel("Change in party-vote share, 2023 → 2026 (percentage points)")
ax.set_title("Ordinary-vote share swing, national (parties ≥ 0.5 % in either year)")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 3. Venue-level results
# One row per venue per election: votes summed over every electorate listing and both sections
# (advance / election day). `home_electorate` is the general-roll seat with most votes there.

# %%
votes, venues, raw_map = places.venue_results(pv)
venues = places.attach_coords(venues, raw_map, geo)
cov = venues.groupby("election_year").agg(venues=("venue_id", "size"), geocoded=("lat", "count"))
cov["pct"] = (cov.geocoded / cov.venues * 100).round(0)
display(cov)

f = votes[votes.party == FOCUS].merge(venues, on=["election_year", "venue_id"])
f["share"] = f.votes / f.total_votes * 100
big = f[f.total_votes >= MIN_VOTES]
display(big.sort_values("share", ascending=False).head(10)[["election_year", "home_electorate", "label", "votes", "total_votes", "share"]].round(1))

# %% [markdown]
# ### Click-popups: full results for a venue
# `venue_table` gives every party's votes and share at a venue (one year, or both years with the swing).
# Used by the maps below: **click a dot** to see the data behind it.

# %%
_by_venue = {k: g.set_index("party").votes for k, g in votes.groupby(["election_year", "venue_id"])}

def venue_table(venue_id, venue_id_2023=None, year=2026):
    """DataFrame of display strings: parties as rows; votes and % for `year`, plus 2023 and the swing when a
    2023 venue is given (then `year` must be 2026)."""
    cols = {year: _by_venue[(year, venue_id)]}
    if venue_id_2023 is not None:
        cols[2023] = _by_venue[(2023, venue_id_2023)]
    t = pd.DataFrame(cols).fillna(0).astype(int)
    t = t[(t > 0).any(axis=1)].sort_values(year, ascending=False)
    pct = t / t.sum() * 100
    years = ([2023] if venue_id_2023 is not None else []) + [year]
    out = pd.DataFrame(index=t.index)
    for y in years:
        out[f"{y} votes"] = t[y].map("{:,}".format)
        out[f"{y} %"] = pct[y].map("{:.1f}".format)
    if venue_id_2023 is not None:
        out["swing (pts)"] = (pct[year] - pct[2023]).map("{:+.1f}".format)
    total = {f"{y} votes": "{:,}".format(t[y].sum()) for y in years} | {f"{y} %": "100.0" for y in years}
    if venue_id_2023 is not None:
        total["swing (pts)"] = ""
    out.loc["Total"] = pd.Series(total)
    return out

# %% [markdown]
# ## 4. Map: where was `FOCUS` strongest? (one layer per election; marker size = venue size)

# %%
def in_bbox(d):
    if BBOX is None:
        return d
    return d[d.lat.between(BBOX[0], BBOX[1]) & d.lon.between(BBOX[2], BBOX[3])]

def share_map(df_by_year, party):
    mapped = pd.concat(df_by_year.values()).dropna(subset=["lat"])
    vmax = float(mapped.share.quantile(0.98))
    cmap = LinearColormap(["#f7fcf5", "#74c476", "#00441b"], vmin=0, vmax=vmax, caption=f"{party} share of party votes (%)")
    m = maps.base_map([mapped.lat.mean(), mapped.lon.mean()], 6 if BBOX is None else 11)
    for year, d in df_by_year.items():
        layer = folium.FeatureGroup(name=str(year), show=(year == max(df_by_year)))
        for r in d.dropna(subset=["lat"]).itertuples():
            folium.CircleMarker(
                [r.lat, r.lon], radius=3 + np.sqrt(r.total_votes) / 8, color="#333", weight=0.4,
                fill=True, fill_color=cmap(min(r.share, vmax)), fill_opacity=0.8,
                tooltip=f"{r.label}<br>{r.home_electorate}<br>{year}: {r.share:.1f}% ({r.votes}/{r.total_votes})",
                popup=maps.popup(r.label, f"{year} · home electorate {r.home_electorate} · ordinary votes", venue_table(r.venue_id, year=year), bold=party),
            ).add_to(layer)
        layer.add_to(m)
    cmap.add_to(m); folium.LayerControl(collapsed=False).add_to(m)
    return m

share_map({y: in_bbox(big[big.election_year == y]) for y in (2023, 2026)}, FOCUS)

# %% [markdown]
# ## 5. Match 2026 venues to 2023 venues by distance
# Mutual nearest neighbours within `MATCH_M` metres, across all electorates. Check the diagnostics before trusting
# the swing: most pairs should be very close, and most should also agree on the venue name.

# %%
a = big[big.election_year == 2026].dropna(subset=["lat"]).reset_index(drop=True)
b = big[big.election_year == 2023].dropna(subset=["lat"]).reset_index(drop=True)
pairs = places.match_by_distance(a, b, max_m=MATCH_M)
sw = pd.DataFrame({
    "label_2026": a.loc[pairs.a_index, "label"].values, "label_2023": b.loc[pairs.b_index, "label"].values,
    "electorate_2026": a.loc[pairs.a_index, "home_electorate"].values, "electorate_2023": b.loc[pairs.b_index, "home_electorate"].values,
    "venue_id_2026": a.loc[pairs.a_index, "venue_id"].values, "venue_id_2023": b.loc[pairs.b_index, "venue_id"].values,
    "same_name": (a.loc[pairs.a_index, "venue_id"].values == b.loc[pairs.b_index, "venue_id"].values),
    "dist_m": pairs.dist_m.values, "lat": a.loc[pairs.a_index, "lat"].values, "lon": a.loc[pairs.a_index, "lon"].values,
    "share_2026": a.loc[pairs.a_index, "share"].values, "share_2023": b.loc[pairs.b_index, "share"].values,
    "votes_2026": a.loc[pairs.a_index, "total_votes"].values, "votes_2023": b.loc[pairs.b_index, "total_votes"].values,
})
sw["swing"] = sw.share_2026 - sw.share_2023
print(f"matched {len(sw)} of {len(a)} 2026 venues and {len(b)} 2023 venues (≥ {MIN_VOTES} votes, geocoded)")
print(f"median distance {sw.dist_m.median():.0f} m; {sw.same_name.mean():.0%} also have the same normalised venue name")
fig, ax = plt.subplots(figsize=(7, 3)); ax.hist(sw.dist_m, bins=30); ax.set_xlabel("distance between matched venues (m)"); plt.show()

# %% [markdown]
# Pairs that do **not** share a name are the ones to eyeball (renamed venues, or a wrong neighbour):

# %%
display(sw[~sw.same_name].sort_values("dist_m", ascending=False).head(12)[["label_2026", "label_2023", "dist_m"]].round(0))

# %% [markdown]
# Biggest swings (venue size ≥ `MIN_VOTES` in both years; 2026 venue size shown):

# %%
display(sw.sort_values("swing", ascending=False).head(8)[["electorate_2026", "label_2026", "share_2023", "share_2026", "swing", "votes_2026"]].round(1))
display(sw.sort_values("swing").head(8)[["electorate_2026", "label_2026", "share_2023", "share_2026", "swing", "votes_2026"]].round(1))

# %% [markdown]
# ## 6. Swing map (click a dot for every party's votes, share and swing at that venue)

# %%
s = in_bbox(sw)
lim = float(np.ceil(s.swing.abs().quantile(0.95)))
cm = LinearColormap(["#b2182b", "#f7f7f7", "#1b7837"], vmin=-lim, vmax=lim, caption=f"{FOCUS} swing 2023→2026 (pts)")
m = maps.base_map([s.lat.mean(), s.lon.mean()], 6 if BBOX is None else 11)
for r in s.itertuples():
    folium.CircleMarker([r.lat, r.lon], radius=3 + np.sqrt(r.votes_2026) / 8, color="#333", weight=0.4, fill=True,
                        fill_color=cm(max(-lim, min(lim, r.swing))), fill_opacity=0.8,
                        tooltip=f"{r.label_2026}<br>{r.share_2023:.1f}% → {r.share_2026:.1f}% ({r.swing:+.1f})",
                        popup=maps.popup(
                            r.label_2026,
                            f"2026 electorate {r.electorate_2026} (2023: {r.electorate_2023})"
                            + ("" if r.same_name else f" · matched to 2023 venue '{r.label_2023}'")
                            + f" · {r.dist_m:.0f} m apart",
                            venue_table(r.venue_id_2026, r.venue_id_2023), bold=FOCUS)).add_to(m)
cm.add_to(m)
m.save(ROOT / "data/geo/swing_map.html")  # open in a browser for a full-screen version
m
