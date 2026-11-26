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
