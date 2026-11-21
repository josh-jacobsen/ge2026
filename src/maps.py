"""One place to choose the map basemap.

The default OpenStreetMap tile server returns 403 'Access blocked' to notebooks (no Referer header; see its tile
usage policy), and folium's built-in CartoDB tiles now ask for an API key. Esri's light-gray canvas needs neither
and keeps the focus on the data. To switch provider, change BASEMAP only.
"""

import folium

BASEMAP = {
    "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    "attr": "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
}


def base_map(location, zoom_start=6) -> folium.Map:
    return folium.Map(location=location, zoom_start=zoom_start, tiles=BASEMAP["tiles"], attr=BASEMAP["attr"])
