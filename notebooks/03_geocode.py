# %% [markdown]
# # 03 – Geocode voting places
# Looks up coordinates with Nominatim (OpenStreetMap) for places not yet in `data/geo/geocode_cache.csv`.
# Only public venue names/addresses are sent, at ~1 request/second, so a big batch takes a while;
# progress is saved every 20 places and re-running resumes where it stopped.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd, folium
import geocode, maps, geocheck

# %% [markdown]
# ## 1. What still needs geocoding?

# %%
todo = geocode.pending_places()
print(f"{len(todo)} places to geocode (~{len(todo) * 1.1 / 60:.0f} min)")
todo[:10]

# %% [markdown]
# ## 2. Run (resumable – interrupt any time)

# %%
geocode.main()

# %% [markdown]
# ## 3. Misses – fix by typing `lat`/`lon` into `data/geo/geocode_cache.csv`
# The script never overwrites cached rows, so manual fixes stick.

# %%
geo = geocode.load_cache()
places = pd.read_parquet(geocode.STAGING / "stg_voting_places.parquet")
fixed = set(places[places.place_kind.isin(["advance", "election_day"])].voting_place_raw)
geo = geo[geo.voting_place_raw.isin(fixed)]
print(f"matched {geo.lat.notna().sum()} / {len(geo)}")
display(geo[geo.lat.isna()][["voting_place_raw"]])

# %% [markdown]
# ## 4. Outliers: pins far from the other venues of their electorate
# Suburb names repeat around the country (Northcote is in Auckland *and* Christchurch), and the geocoder only checks
# that a hit is somewhere in New Zealand. Here each general electorate gets a centre (median of its geocoded
# election-day venues) and a venue is flagged if it is farther away than `max(30 km, 3 × the electorate's median
# distance)`. Māori electorates and electorates with fewer than 5 geocoded venues are not checked.
#
# **Fix a flagged pin** by correcting `lat`/`lon` in `data/geo/geocode_cache.csv` (set `matched_query` to `manual`),
# then re-run this notebook from the top of this section. A wrong pin that is *not* flagged (e.g. the right suburb
# name in the wrong part of the same electorate) is not caught here, so also skim the map in step 5.

# %%
home = geocheck.home_electorates(pd.read_parquet(geocode.STAGING / "stg_party_votes.parquet"))
pts = (home.merge(geo[["voting_place_raw", "lat", "lon"]], on="voting_place_raw")
           .rename(columns={"electorate": "group", "voting_place_raw": "label"}))
checked = geocheck.flag_outliers(pts)
n_groups = checked.groupby("group").size().ge(5).sum()
flagged = checked[checked.outlier].drop_duplicates("label")
print(f"{len(checked.drop_duplicates('label'))} venues checked in {n_groups} electorates; {len(flagged)} flagged")
display(flagged[["group", "label", "distance_km", "threshold_km", "lat", "lon"]].round(1))

# %%
if len(flagged):
    mo = maps.base_map([flagged.lat.mean(), flagged.lon.mean()], 5)
    for r in flagged.itertuples():
        folium.CircleMarker([r.lat, r.lon], radius=7, color="#b2182b", fill=True, tooltip=f"{r.label}<br>{r.group}: {r.distance_km:.0f} km from its electorate's centre").add_to(mo)
        folium.PolyLine([[r.lat, r.lon], [r.centre_lat, r.centre_lon]], color="#b2182b", weight=1, dash_array="4").add_to(mo)
    display(mo)

# %% [markdown]
# ## 5. Eyeball the matches (hover = original label, click = geocoder's address)

# %%
ok = geo.dropna(subset=["lat"])
m = maps.base_map([ok.lat.mean(), ok.lon.mean()], 6)
for r in ok.itertuples():
    folium.CircleMarker([r.lat, r.lon], radius=4, tooltip=r.voting_place_raw, popup=r.display_name).add_to(m)
m
