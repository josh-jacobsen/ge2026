"""Click-popup HTML for the maps (no network, no raw data)."""

import re

import pandas as pd

import maps


def table():
    return pd.DataFrame({"2026 votes": ["10", "5", "15"], "2026 %": ["66.7", "33.3", "100.0"]},
                        index=["Green Party", "ACT <b>New Zealand</b>", "Total"])


def html_of(popup) -> str:
    return popup.html.render()


def test_popup_contains_title_subtitle_and_every_row():
    h = html_of(maps.popup("Albany Hub", "2026 · North Shore", table()))
    for text in ("Albany Hub", "2026 · North Shore", "Green Party", "66.7", "Total", "100.0"):
        assert text in h


def test_popup_escapes_html_in_labels():
    h = html_of(maps.popup("<script>x</script>", "sub", table()))
    assert "<script>x</script>" not in h and "&lt;script&gt;" in h
    assert "ACT &lt;b&gt;New Zealand&lt;/b&gt;" in h


def test_popup_highlights_only_the_requested_row():
    h = html_of(maps.popup("t", "s", table(), bold="Green Party"))
    assert h.count("background:#eef6ee") == 1


def legend_html(**kw):
    import folium

    m = folium.Map()
    maps.legend(m, **kw)
    return m.get_root().render()


def test_legend_is_collapsible_and_lists_every_ramp_and_key():
    h = legend_html(ramps=[("Swing (pts)", ["#b2182b", "#f7f7f7", "#1b7837"], "-5", "+5")],
                    keys=[("#1f77b4", "2026 only", True), ("#bdbdbd", "too few votes", False)])
    assert "<details open" in h and "<summary" in h          # minimisable, open by default
    for text in ("Swing (pts)", "-5", "+5", "2026 only", "too few votes", "linear-gradient"):
        assert text in h


def test_legend_escapes_html_in_text():
    h = legend_html(ramps=[("<script>x</script>", ["#fff", "#000"], "0", "1")], title="<b>t</b>")
    assert "<script>x</script>" not in h and "&lt;script&gt;" in h and "&lt;b&gt;t&lt;/b&gt;" in h


def test_basemap_is_not_listed_in_the_layer_control():
    import folium

    m = maps.base_map([-41, 174])
    folium.LayerControl().add_to(m)
    h = m.get_root().render()
    assert "arcgisonline" in h                       # tiles still loaded
    assert re.search(r"base_layers\s*:\s*\{\s*\}", h)      # no switchable base layers listed
