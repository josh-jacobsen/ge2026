import json
from datetime import date

import pandas as pd
import pytest

import campaign

needs_exports = pytest.mark.skipif(not any(campaign.RAW.glob("*.csv")),
                                reason="campaign exports are sensitive and not in the repo; these tests need them locally")

HEADER = "Contact Week,Attempts,Contacts,Contact %,Meaningful Interactions,MI %\n"
WEEK41 = '"Oct 9, 2023 to Oct 15, 2023 (Week 41)"'
WEEK42 = '"Oct 16, 2023 to Oct 22, 2023 (Week 42)"'


def write(tmp_path, body, name="north_shore_2023_phone_calls.csv"):
    p = tmp_path / name
    p.write_text(HEADER + body)
    return p


# ---- week labels and the election-week alignment -------------------------------------------------------------------

def test_parse_week():
    assert campaign.parse_week("Oct 9, 2023 to Oct 15, 2023 (Week 41)") == (date(2023, 10, 9), date(2023, 10, 15), 41)


@pytest.mark.parametrize("label", [
    "Oct 10, 2023 to Oct 16, 2023 (Week 41)",    # starts on a Tuesday
    "Oct 9, 2023 to Oct 14, 2023 (Week 41)",     # six days
    "Oct 9, 2023 to Oct 15, 2023 (Week 40)",     # wrong ISO week number
    "Week 41",
])
def test_parse_week_rejects_bad_labels(label):
    with pytest.raises(ValueError):
        campaign.parse_week(label)


def test_election_days_are_saturdays_and_election_week_is_zero():
    assert all(d.weekday() == 5 for d in campaign.ELECTION_DATES.values())
    assert campaign.weeks_to_election(date(2023, 10, 9), 2023) == 0     # week containing 14 Oct 2023
    assert campaign.weeks_to_election(date(2026, 11, 2), 2026) == 0     # week containing 7 Nov 2026
    assert campaign.weeks_to_election(date(2026, 10, 26), 2026) == 1
    assert campaign.weeks_to_election(date(2023, 10, 16), 2023) == -1   # after the vote


def test_2026_week_n_lines_up_with_2023_week_n_minus_4():
    assert campaign.weeks_to_election(date(2026, 10, 5), 2026) == campaign.weeks_to_election(date(2023, 9, 11), 2023) == 4


# ---- validation of one export --------------------------------------------------------------------------------------

def test_load_file_reads_a_valid_export(tmp_path):
    p = write(tmp_path, f"{WEEK42},10,4,0.4,2,0.5\n{WEEK41},100,30,0.3,15,0.5\n")
    d = campaign.load_file(p)
    assert d.seat.unique().tolist() == ["North Shore"] and d.year.unique().tolist() == [2023]
    assert d.week_start.tolist() == [date(2023, 10, 16), date(2023, 10, 9)]
    assert d.weeks_to_election.tolist() == [-1, 0]
    assert d.attempts.sum() == 110 and d.meaningful.sum() == 17


@pytest.mark.parametrize("row, why", [
    (f"{WEEK41},10,11,1.1,0,0", "contacts above attempts"),
    (f"{WEEK41},10,4,0.4,5,1.25", "meaningful above contacts"),
    (f"{WEEK41},10,4,0.5,2,0.5", "Contact % does not match"),
    (f"{WEEK41},10,4,0.4,2,0.9", "MI % does not match"),
    (f"{WEEK41},10,4,0.4,2,0.5\n{WEEK41},5,1,0.2,0,0", "duplicate week"),
    ('"Oct 9, 2026 to Oct 15, 2026 (Week 41)",10,4,0.4,2,0.5', "week outside the file's year"),
])
def test_load_file_rejects_inconsistent_rows(tmp_path, row, why):
    with pytest.raises(ValueError):
        campaign.load_file(write(tmp_path, row + "\n"))


def test_zero_contacts_may_have_any_mi_rate_of_zero(tmp_path):
    d = campaign.load_file(write(tmp_path, f"{WEEK41},3,0,0,0,0\n"))
    assert d.contacts.iloc[0] == 0


def test_load_file_rejects_bad_names_and_columns(tmp_path):
    with pytest.raises(ValueError):
        campaign.load_file(write(tmp_path, f"{WEEK41},10,4,0.4,2,0.5\n", name="mt_albert_2023_phone_calls.csv"))
    bad = tmp_path / "northcote_2023_phone_calls.csv"
    bad.write_text("Week,Attempts\n1,2\n")
    with pytest.raises(ValueError):
        campaign.load_file(bad)


def test_summarize_rates_are_none_without_a_denominator():
    df = pd.DataFrame({"seat": ["A", "A"], "attempts": [3, 0], "contacts": [0, 0], "meaningful": [0, 0]})
    t = campaign.summarize(df, ["seat"])
    assert t.loc["A", "attempts"] == 3 and pd.isna(t.loc["A", "meaningful_rate"]) and t.loc["A", "contact_rate"] == 0


# ---- the 16 real exports, pinned -----------------------------------------------------------------------------------
# The pinned totals are sensitive too, so they live in data/raw/campaign/pinned_totals.json (gitignored), not in this file:
# {"totals": {file: [rows, attempts, contacts, meaningful]}, "after_election": {file: attempts dated after election week}}.
PINNED = campaign.RAW / "pinned_totals.json"


def pinned():
    return json.loads(PINNED.read_text())


@needs_exports
def test_all_sixteen_exports_are_present_and_load():
    assert sorted(p.name for p in campaign.RAW.glob("*.csv")) == sorted(pinned()["totals"])
    for name in pinned()["totals"]:
        campaign.load_file(campaign.RAW / name)


@needs_exports
def test_each_export_matches_its_pinned_totals():
    for name, (rows, att, con, mi) in pinned()["totals"].items():
        d = campaign.load_file(campaign.RAW / name)
        assert (len(d), d.attempts.sum(), d.contacts.sum(), d.meaningful.sum()) == (rows, att, con, mi), name


@needs_exports
def test_load_all_drops_only_the_weeks_after_the_election():
    totals, after = pinned()["totals"], pinned()["after_election"]
    full = campaign.load_all(through_election=False)
    cut = campaign.load_all()
    assert full.attempts.sum() == sum(v[1] for v in totals.values())
    assert full.attempts.sum() - cut.attempts.sum() == sum(after.values())
    assert (cut.weeks_to_election >= 0).all()
    gone = full[full.weeks_to_election < 0]
    got = gone.assign(f=gone.seat.str.lower().str.replace(" ", "_") + "_" + gone.year.astype(str) + "_" + gone.channel + ".csv")
    assert got.groupby("f").attempts.sum().to_dict() == after


@needs_exports
def test_every_seat_year_channel_is_present():
    d = campaign.load_all()
    assert len(d.groupby(["seat", "year", "channel"])) == 4 * 2 * 2
