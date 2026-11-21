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
import geocode

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
# ## 4. Eyeball the matches (hover = original label, click = geocoder's address)

# %%
ok = geo.dropna(subset=["lat"])
m = folium.Map(location=[ok.lat.mean(), ok.lon.mean()], zoom_start=6, tiles="OpenStreetMap")
for r in ok.itertuples():
    folium.CircleMarker([r.lat, r.lon], radius=4, tooltip=r.voting_place_raw, popup=r.display_name).add_to(m)
m
