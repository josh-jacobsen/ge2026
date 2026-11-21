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


def popup(title: str, subtitle: str, table, bold: str | None = None, max_width: int = 560) -> folium.Popup:
    """Click-popup for a marker: heading, one line of context, then a table (a DataFrame of display strings).

    The row whose index equals `bold` is highlighted (e.g. the party being mapped). All text is HTML-escaped.
    """
    from html import escape

    head = "".join(f"<th style='text-align:right;padding:1px 6px'>{escape(str(c))}</th>" for c in table.columns)
    body = []
    for idx, row in table.iterrows():
        style = "font-weight:bold;background:#eef6ee" if idx == bold else ("border-top:1px solid #999;font-weight:bold" if idx == "Total" else "")
        cells = "".join(f"<td style='text-align:right;padding:1px 6px'>{escape(str(v))}</td>" for v in row)
        body.append(f"<tr style='{style}'><td style='padding:1px 6px'>{escape(str(idx))}</td>{cells}</tr>")
    html = (
        f"<div style='font:12px/1.35 sans-serif'><b>{escape(title)}</b><br><span style='color:#555'>{escape(subtitle)}</span>"
        f"<table style='border-collapse:collapse;margin-top:6px;font-size:11px'><tr><th></th>{head}</tr>{''.join(body)}</table></div>"
    )
    return folium.Popup(folium.Html(html, script=True), max_width=max_width)
