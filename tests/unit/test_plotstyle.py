import pytest

import plotstyle


def test_each_seat_gets_a_distinct_marker_in_the_given_order():
    m = plotstyle.seat_markers(["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"])
    assert list(m.values()) == ["o", "s", "^", "p"]
    assert len(set(m.values())) == 4


def test_too_many_seats_is_an_error_not_a_repeated_marker():
    with pytest.raises(ValueError):
        plotstyle.seat_markers([f"seat {i}" for i in range(len(plotstyle.MARKERS) + 1)])
