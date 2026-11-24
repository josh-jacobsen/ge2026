import pandas as pd

import electorates


def test_align_2023_renames_only_2023_rows():
    df = pd.DataFrame({"election_year": [2023, 2026, 2023], "electorate": ["East Coast", "East Cape", "Dunedin"]})
    assert electorates.align_2023(df).electorate.tolist() == ["East Cape", "East Cape", "Dunedin"]


def test_predecessors_are_not_2026_names():
    assert not set(electorates.PREDECESSOR.values()) & set(electorates.PREDECESSOR)


def test_seat_overlap_covers_renamed_seats():
    s = electorates.seat_overlap()
    assert len(s) == 71 and s.notna().all()
    assert s["East Cape"] == 100.0
