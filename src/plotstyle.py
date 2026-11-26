"""Shared chart conventions.

Colour means a party in these notebooks (Green green, Labour red, ...), so electorates are told apart by marker
shape, never by colour. `seat_markers` gives each electorate its own shape, in a fixed order so the same seat looks
the same in every chart.
"""

MARKERS = ["o", "s", "^", "p", "D", "v", "h", "*"]   # circle, square, triangle, pentagon, diamond, ...


def seat_markers(seats) -> dict[str, str]:
    seats = list(seats)
    if len(seats) > len(MARKERS):
        raise ValueError(f"only {len(MARKERS)} distinct marker shapes for {len(seats)} electorates")
    return dict(zip(seats, MARKERS))


def trend_line(ax, x, y, provisional_last: bool = False, marker: str = "o", **kw):
    """Line with markers; if `provisional_last`, the final point is hollow and joined by a dashed segment (a count that is
    not final yet). NaN values leave a gap. Extra keywords (color, label, ms, ...) go to the solid line."""
    import pandas as pd

    x, y = list(x), pd.Series(list(y), dtype=float)
    if not provisional_last:
        ax.plot(x, y, marker=marker, **kw)
        return
    (line,) = ax.plot(x[:-1], y.iloc[:-1], marker=marker, **kw)
    color = line.get_color()
    ax.plot(x[-2:], y.iloc[-2:], ls="--", color=color, lw=1)
    ax.plot([x[-1]], [y.iloc[-1]], marker=marker, mfc="white", color=color, ls="none", ms=kw.get("ms", 6))
