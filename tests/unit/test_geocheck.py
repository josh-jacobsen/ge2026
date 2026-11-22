"""Outlier check for geocoded venues (synthetic data, no network, no raw files)."""

import pandas as pd

from geocheck import flag_outliers, home_electorates


def pts(group, coords, prefix):
    return [{"group": group, "label": f"{prefix} {i}", "lat": la, "lon": lo} for i, (la, lo) in enumerate(coords)]


AUCKLAND = [(-36.80 + i * 0.005, 174.74 + i * 0.004) for i in range(8)]  # a compact urban electorate


def test_wrong_city_hit_is_flagged():
    # a Christchurch 'Northcote' pinned among Auckland venues: ~760 km away
    p = pd.DataFrame(pts("Northcote", AUCKLAND, "ok") + [{"group": "Northcote", "label": "wrong", "lat": -43.50, "lon": 172.63}])
    r = flag_outliers(p)
    assert list(r[r.outlier].label) == ["wrong"]
    assert r.distance_km.iloc[0] > 700  # sorted farthest first


def test_compact_electorate_with_no_strays_flags_nothing():
    assert not flag_outliers(pd.DataFrame(pts("Northcote", AUCKLAND, "ok"))).outlier.any()


def test_big_rural_electorate_is_not_flagged_for_being_big():
    # venues spread ~0.5 degrees (~55 km) apart: a 60 km spread is normal here, so nothing should be flagged
    rural = [(-45.0 + (i % 4) * 0.4, 168.5 + (i // 4) * 0.5) for i in range(12)]
    assert not flag_outliers(pd.DataFrame(pts("Southland", rural, "r"))).outlier.any()


def test_tiny_groups_are_never_flagged():
    p = pd.DataFrame(pts("Few", AUCKLAND[:3], "ok") + [{"group": "Few", "label": "far", "lat": -43.5, "lon": 172.6}])
    assert not flag_outliers(p, min_points=5).outlier.any()


def test_rows_without_coordinates_are_ignored():
    p = pd.DataFrame(pts("Northcote", AUCKLAND, "ok") + [{"group": "Northcote", "label": "none", "lat": None, "lon": None}])
    r = flag_outliers(p)
    assert "none" not in set(r.label)


def test_home_electorate_is_general_roll_election_day_majority():
    place = "Albany, Albany Hall, Library Lane"
    rows = [
        (2023, "North Shore", place, "election_day", 10),
        (2023, "Upper Harbour", place, "election_day", 40),
        (2023, "Te Tai Tokerau", place, "election_day", 99),   # Māori seat: never home
        (2023, "North Shore", place, "advance", 500),           # advance: ignored
    ]
    pv = pd.DataFrame(rows, columns=["election_year", "electorate", "voting_place_raw", "place_kind", "votes"])
    h = home_electorates(pv)
    assert len(h) == 1 and h.electorate.iloc[0] == "Upper Harbour"
