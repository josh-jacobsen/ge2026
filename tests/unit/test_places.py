"""Venue-level aggregation and distance matching (synthetic data, no raw files needed)."""

import pandas as pd

from places import haversine_m, match_by_distance, venue_id, venue_results


def test_haversine_known_distance():
    # Auckland Sky Tower to Wellington Beehive is about 493 km
    d = haversine_m(-36.8485, 174.7622, -41.2784, 174.7767)
    assert 490_000 < d < 497_000


def frame(*points):
    return pd.DataFrame(points, columns=["lat", "lon"])


def test_match_pairs_nearest_within_threshold():
    a = frame((-36.8500, 174.7600), (-41.2800, 174.7800))
    b = frame((-36.8501, 174.7601), (-41.2801, 174.7801))
    m = match_by_distance(a, b, max_m=300)
    assert list(zip(m.a_index, m.b_index)) == [(0, 0), (1, 1)]
    assert (m.dist_m < 50).all()


def test_match_rejects_far_pairs():
    a = frame((-36.85, 174.76))
    b = frame((-36.90, 174.76))  # ~5.5 km away
    assert match_by_distance(a, b, max_m=300).empty


def test_match_is_one_to_one_mutual_nearest():
    # two 2026 venues share one close 2023 venue: only the closer one may claim it
    a = frame((-36.8500, 174.7600), (-36.8503, 174.7600))
    b = frame((-36.8501, 174.7600))
    m = match_by_distance(a, b, max_m=300)
    assert len(m) == 1 and m.a_index.iloc[0] == 0


def test_match_ignores_missing_coordinates():
    a = pd.DataFrame({"lat": [None, -36.85], "lon": [None, 174.76]})
    b = frame((-36.85, 174.76))
    m = match_by_distance(a, b)
    assert list(m.a_index) == [1]


def test_venue_id_ignores_address_suffix_letters_and_case():
    assert venue_id("Albany, Albany Community Hub, 575 Albany Highway") == venue_id("Albany, ALBANY community hub, 575a Albany Highway")


def test_venue_results_sums_across_electorates_and_sections():
    place = "Albany, Albany Community Hub, 575 Albany Highway"
    rows = [
        # same venue listed under two general electorates, advance + election day, plus a Māori overlay
        (2023, "North Shore", place, "advance", "Green Party", 10),
        (2023, "Upper Harbour", place, "advance", "Green Party", 5),
        (2023, "Upper Harbour", place, "election_day", "Green Party", 20),
        (2023, "Te Tai Tokerau", place, "election_day", "Green Party", 1),
        (2023, "North Shore", place, "special", "Green Party", 99),  # not ordinary: excluded
    ]
    pv = pd.DataFrame(rows, columns=["election_year", "electorate", "voting_place_raw", "place_kind", "party", "votes"])
    votes, venues, raw_map = venue_results(pv)
    assert votes.votes.sum() == 36
    assert len(venues) == 1 and venues.total_votes.iloc[0] == 36
    assert venues.home_electorate.iloc[0] == "Upper Harbour"  # 25 vs 10; the Māori seat never counts as home


def test_booths_venue_table_sums_venue_and_tracks_home_votes():
    from booths import top_n, venue_table

    place = "Milford, Milford Shopping Centre, 24 Milford Road"
    other = "Takapuna, Shore City, Lake Road"
    rows = []
    for el, kind, party, v in [
        ("North Shore", "advance", "Green Party", 60), ("North Shore", "advance", "National Party", 140),
        ("Northcote", "advance", "Green Party", 5), ("Northcote", "advance", "National Party", 15),
        ("Te Tai Tokerau", "election_day", "Green Party", 2), ("North Shore", "special", "Green Party", 99),
    ]:
        rows.append((2026, el, place, kind, party, v))
    rows += [(2026, "North Shore", other, "advance", "Green Party", 30), (2026, "North Shore", other, "advance", "National Party", 10)]
    pv = pd.DataFrame(rows, columns=["election_year", "electorate", "voting_place_raw", "place_kind", "party", "votes"])
    vt = venue_table(pv).set_index("suburb")
    m = vt.loc["Milford"]
    assert (m.green, m.green_home, m.total, m.home_total, m.n_electorates) == (67, 60, 222, 200, 3)  # special vote excluded
    assert m.home_electorate == "North Shore" and m.top == 0
    t = top_n(venue_table(pv), "green", "pct", min_votes=50)  # Takapuna has only 40 votes: out of the share ranking
    assert list(t.suburb) == ["Milford"]
    assert round(top_n(venue_table(pv), "green", "votes").set_index("suburb").loc["Milford", "home_pct"], 1) == 89.6
