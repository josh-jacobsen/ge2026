import pytest

import plotstyle


def test_each_seat_gets_a_distinct_marker_in_the_given_order():
    m = plotstyle.seat_markers(["North Shore", "Northcote", "East Coast Bays", "Upper Harbour"])
    assert list(m.values()) == ["o", "s", "^", "p"]
    assert len(set(m.values())) == 4


def test_too_many_seats_is_an_error_not_a_repeated_marker():
    with pytest.raises(ValueError):
        plotstyle.seat_markers([f"seat {i}" for i in range(len(plotstyle.MARKERS) + 1)])


def test_trend_line_marks_the_last_point_hollow_and_dashed():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    plotstyle.trend_line(ax, [2017, 2020, 2023, 2026], [1, 2, 3, 4], provisional_last=True, color="k", label="s")
    solid, dashed, last = ax.lines
    assert list(solid.get_xdata()) == [2017, 2020, 2023] and dashed.get_linestyle() == "--"
    assert list(last.get_xdata()) == [2026] and last.get_markerfacecolor() == "white"
    plt.close(fig)
    fig, ax = plt.subplots()
    plotstyle.trend_line(ax, [1, 2], [1, 2])
    assert len(ax.lines) == 1                     # final result: one plain line
    plt.close(fig)
