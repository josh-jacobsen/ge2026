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
    # control=False keeps the basemap out of the layer switcher (otherwise it is listed under its full tile URL)
    m = folium.Map(location=location, zoom_start=zoom_start, tiles=None)
    folium.TileLayer(tiles=BASEMAP["tiles"], attr=BASEMAP["attr"], name="Basemap", control=False).add_to(m)
    return m


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


def legend(m: folium.Map, ramps, keys=(), title: str = "Legend") -> None:
    """Small collapsible legend pinned to the bottom-left of the map (click the title to minimise it).

    `ramps`: (caption, [css colors low→high], low label, high label) for each colour scale.
    `keys`: (css color, label, ring) for each marker key; ring=True draws a thick outline instead of a filled dot.
    Uses a native <details> element, so it needs no JavaScript. All text is HTML-escaped.
    """
    from html import escape

    parts = []
    for caption, colors, lo, hi in ramps:
        bar = f"linear-gradient(to right,{','.join(escape(c) for c in colors)})"
        parts.append(
            f"<div style='margin-top:5px'>{escape(caption)}</div>"
            f"<div style='height:7px;width:150px;border-radius:2px;background:{bar}'></div>"
            f"<div style='display:flex;justify-content:space-between;width:150px;color:#555'><span>{escape(lo)}</span><span>{escape(hi)}</span></div>"
        )
    for color, label, ring in keys:
        dot = (f"border:2.5px solid {escape(color)};background:transparent" if ring else f"background:{escape(color)}")
        parts.append(f"<div style='margin-top:4px;display:flex;align-items:center;gap:6px'><span style='width:9px;height:9px;border-radius:50%;display:inline-block;{dot}'></span>{escape(label)}</div>")
    html = (
        "<details open id='map-legend' style=\"position:fixed;bottom:22px;left:10px;z-index:9999;background:rgba(255,255,255,.92);"
        "padding:4px 8px;border-radius:5px;box-shadow:0 1px 4px rgba(0,0,0,.3);font:11px/1.25 sans-serif;max-width:200px\">"
        f"<summary style='cursor:pointer;font-weight:bold;outline:none'>{escape(title)}</summary>{''.join(parts)}</details>"
    )
    m.get_root().html.add_child(folium.Element(html))
