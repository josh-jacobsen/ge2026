import pandas as pd

import focus_history as fh


def seat_rows():
    rows = []
    for party, votes in [("Labour Party", 30), ("Green Party", 10), ("The Opportunities Party (TOP)", 5),
                         ("National Party", 40), ("ACT New Zealand", 10), ("New Zealand First Party", 3), ("Conservative", 2)]:
        rows.append({"election_year": 2023, "electorate": "X", "vote_type": "party", "party": party, "votes": votes})
    return pd.DataFrame(rows)


def test_bloc_shares_add_up_and_use_all_valid_votes():
    b = fh.bloc_shares(seat_rows(), "party").loc[("X", 2023)]
    assert b["Left"] == 45 and b["Right"] == 53          # of 100 votes
    assert abs(b["Other"] - 2) < 1e-9                    # Conservative only
    assert abs(b["Left"] + b["Right"] + b["Other"] - 100) < 1e-9
    assert b["lead (Left - Right)"] == -8
    assert abs(b["Left of two-bloc"] - 45 / 98 * 100) < 1e-9


def test_a_bloc_member_missing_from_a_seat_counts_as_zero_votes():
    d = seat_rows()
    d = d[d.party != "The Opportunities Party (TOP)"]     # e.g. TOP stood no candidate
    assert fh.bloc_shares(d, "party").loc[("X", 2023), "Left"] == 40 / 95 * 100


def test_party_names_are_merged_across_elections():
    assert fh.canon("New Conservatives") == fh.canon("Conservative") == "Conservative"
    assert fh.canon("Māori Party") == fh.canon("Te Pāti Māori")
    assert fh.canon("Labour Party") == "Labour Party"


def test_history_file_has_every_focus_seat_year_and_vote_type():
    h = pd.read_csv(fh.ROOT / "data/reference/focus_seats_history.csv")
    seats = {"North Shore", "Northcote", "East Coast Bays", "Upper Harbour"}
    got = h.groupby(["election_year", "electorate", "vote_type"]).votes.sum()
    for year in (2017, 2020):
        for seat in seats:
            for kind in ("party", "candidate"):
                assert got.loc[(year, seat, kind)] > 25_000, (year, seat, kind)


def test_bloc_breakdown_members_add_to_their_bloc_and_match_bloc_shares():
    d = seat_rows()
    b = fh.bloc_breakdown(d, "party").loc[("X", 2023)]
    assert abs(b["Labour"] + b["Green"] + b["TOP"] - b["Left"]) < 1e-9
    assert abs(b["National"] + b["ACT"] + b["NZ First"] - b["Right"]) < 1e-9
    assert abs(b["Left"] + b["Right"] + b["Other"] - 100) < 1e-9
    assert b["Left"] == fh.bloc_shares(d, "party").loc[("X", 2023), "Left"]
    assert list(fh.bloc_breakdown(d, "party").columns) == ["Labour", "Green", "TOP", "Left", "National", "ACT", "NZ First", "Right", "Other", "lead (Left - Right)"]


def test_bloc_breakdown_gives_zero_for_a_party_that_stood_nobody():
    d = seat_rows()
    d = d[d.party != "The Opportunities Party (TOP)"]
    assert fh.bloc_breakdown(d, "party").loc[("X", 2023), "TOP"] == 0
