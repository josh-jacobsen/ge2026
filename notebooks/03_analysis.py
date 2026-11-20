# %% [markdown]
# # 03 – 2026 vs 2023 analysis
# Like-for-like: **ordinary places only** (`advance` + `election_day`), since 2026 is preliminary
# and has no special votes. Change `FOCUS` to look at any party.

# %%
from pathlib import Path
import numpy as np, pandas as pd, folium
import matplotlib.pyplot as plt
from branca.colormap import LinearColormap

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
ST = ROOT / "data/staging"
FOCUS = "Green Party"
ORDINARY = ["advance", "election_day"]
pd.set_option("display.width", 200, "display.max_columns", 30)

pv = pd.read_parquet(ST / "stg_party_votes.parquet")
pv = pv[pv.place_kind.isin(ORDINARY)]
geo = pd.read_csv(ROOT / "data/geo/geocode_cache.csv")[["voting_place_raw", "lat", "lon"]]

# %% [markdown]
# ## 1. Party vote share by electorate

# %%
def share(df, by):
    t = df.groupby(by + ["party"])["votes"].sum().reset_index()
    t["share"] = t.votes / t.groupby(by)["votes"].transform("sum") * 100
    return t

by_elec = share(pv, ["election_year", "electorate"])
wide = by_elec.pivot_table(index=["electorate", "party"], columns="election_year", values="share")
wide["swing_pts"] = wide[2026] - wide[2023]
display(wide.round(2).sort_values("swing_pts").groupby("electorate").tail(3))
display(wide.xs(FOCUS, level="party").round(2))

# %% [markdown]
# ## 2. Swing by party across all four electorates

# %%
tot = share(pv, ["election_year"]).pivot(index="party", columns="election_year", values="share")
tot["swing_pts"] = tot[2026] - tot[2023]
tot = tot.sort_values("swing_pts")
ax = tot["swing_pts"].plot.barh(figsize=(8, 6), color=np.where(tot["swing_pts"] > 0, "#2a9d8f", "#c1666b"))
ax.set_xlabel("Change in party-vote share, 2023 → 2026 (percentage points)")
ax.set_title("Ordinary-vote share swing, four North Shore electorates")
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 3. Voting-place level: share of `FOCUS` party

# %%
place = share(pv, ["election_year", "electorate", "voting_place_raw"])
f = place[place.party == FOCUS].merge(geo, on="voting_place_raw", how="left")
tot_votes = pv.groupby(["election_year", "electorate", "voting_place_raw"])["votes"].sum().rename("place_total").reset_index()
f = f.merge(tot_votes, on=["election_year", "electorate", "voting_place_raw"])
MIN_VOTES = 100  # ignore tiny places: shares are noisy (and <6 votes are zeroed by the Commission)
big = f[f.place_total >= MIN_VOTES]
display(big.sort_values("share", ascending=False).head(10)[["election_year", "electorate", "voting_place_raw", "votes", "place_total", "share"]].round(1))

# %% [markdown]
# ## 4. Map: where was `FOCUS` strongest? (one layer per election)

# %%
def share_map(df_by_year, title_party):
    mapped = pd.concat(df_by_year.values()).dropna(subset=["lat"])
    vmax = float(mapped.share.quantile(0.98))
    cmap = LinearColormap(["#f7fcf5", "#74c476", "#00441b"], vmin=0, vmax=vmax, caption=f"{title_party} share of party votes (%)")
    m = folium.Map(location=[mapped.lat.mean(), mapped.lon.mean()], zoom_start=11, tiles="cartodbpositron")
    for year, d in df_by_year.items():
        layer = folium.FeatureGroup(name=str(year), show=(year == max(df_by_year)))
        for r in d.dropna(subset=["lat"]).itertuples():
            folium.CircleMarker(
                [r.lat, r.lon], radius=4 + np.sqrt(r.place_total) / 6, color="#333", weight=0.5,
                fill=True, fill_color=cmap(min(r.share, vmax)), fill_opacity=0.85,
                tooltip=f"{r.voting_place_raw}<br>{year}: {r.share:.1f}% ({r.votes}/{r.place_total})",
            ).add_to(layer)
        layer.add_to(m)
    cmap.add_to(m); folium.LayerControl(collapsed=False).add_to(m)
    return m

share_map({y: big[big.election_year == y] for y in (2023, 2026)}, FOCUS)

# %% [markdown]
# ## 5. Swing map – match each 2026 place to the nearest 2023 place (≤ 300 m, same electorate)
# Places are matched by geocoded location because venue names/addresses are spelled differently between years.

# %%
def haversine_m(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 12742000 * np.arcsin(np.sqrt(a))

MATCH_M = 300
a = big[(big.election_year == 2026)].dropna(subset=["lat"]).reset_index(drop=True)
b = big[(big.election_year == 2023)].dropna(subset=["lat"]).reset_index(drop=True)
rows = []
for r in a.itertuples():
    cand = b[b.electorate == r.electorate]
    if cand.empty:
        continue
    d = haversine_m(r.lat, r.lon, cand.lat.values, cand.lon.values)
    i = d.argmin()
    if d[i] <= MATCH_M:
        o = cand.iloc[i]
        rows.append({"electorate": r.electorate, "place_2026": r.voting_place_raw, "place_2023": o.voting_place_raw, "dist_m": d[i],
                     "lat": r.lat, "lon": r.lon, "share_2026": r.share, "share_2023": o.share, "votes_2026": r.place_total})
sw = pd.DataFrame(rows)
sw["swing"] = sw.share_2026 - sw.share_2023
print(f"matched {len(sw)} of {len(a)} 2026 places")
display(sw.sort_values("swing", ascending=False).head(8).round(1))
display(sw.sort_values("swing").head(8).round(1))

# %%
lim = float(np.ceil(sw.swing.abs().quantile(0.95)))
cm = LinearColormap(["#b2182b", "#f7f7f7", "#1b7837"], vmin=-lim, vmax=lim, caption=f"{FOCUS} swing 2023→2026 (pts)")
m = folium.Map(location=[sw.lat.mean(), sw.lon.mean()], zoom_start=11, tiles="cartodbpositron")
for r in sw.itertuples():
    folium.CircleMarker([r.lat, r.lon], radius=4 + np.sqrt(r.votes_2026) / 6, color="#333", weight=0.5, fill=True,
                        fill_color=cm(max(-lim, min(lim, r.swing))), fill_opacity=0.85,
                        tooltip=f"{r.place_2026}<br>{r.share_2023:.1f}% → {r.share_2026:.1f}% ({r.swing:+.1f})").add_to(m)
cm.add_to(m)
m.save(ROOT / "data/geo/swing_map.html")  # open in a browser for a full-screen version
m
