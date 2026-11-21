"""Click-popup HTML for the maps (no network, no raw data)."""

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
