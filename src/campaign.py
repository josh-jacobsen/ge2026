"""Campaign effort (door knocking and phone calling) for the four focus seats, 2023 and 2026.

Source: weekly exports pasted from the campaign tool into `data/raw/campaign/<seat>_<year>_<channel>.csv`, with columns
`Contact Week, Attempts, Contacts, Contact %, Meaningful Interactions, MI %`. Weeks run Monday to Sunday and the label
carries the ISO week number, e.g. "Oct 9, 2023 to Oct 15, 2023 (Week 41)". Weeks with no activity are absent from an
export, so a missing week means zero or not recorded; the files cannot tell the two apart.

Weeks are aligned by `weeks_to_election`: 0 is the week that contains election day (both elections were on a Saturday),
1 is the week before it, and so on. Rows after election week are not campaign effort and are dropped by default.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/campaign"

ELECTION_DATES = {2023: date(2023, 10, 14), 2026: date(2026, 11, 7)}
SEATS = {"north_shore": "North Shore", "northcote": "Northcote",
         "east_coast_bays": "East Coast Bays", "upper_harbour": "Upper Harbour"}
CHANNELS = {"door_knocking": "Door knocking", "phone_calls": "Phone calls"}
COLUMNS = ["Contact Week", "Attempts", "Contacts", "Contact %", "Meaningful Interactions", "MI %"]

_FILE = re.compile(r"^(?P<seat>[a-z_]+)_(?P<year>20\d\d)_(?P<channel>door_knocking|phone_calls)\.csv$")
_WEEK = re.compile(r"^(?P<a>[A-Z][a-z]{2} \d{1,2}, \d{4}) to (?P<b>[A-Z][a-z]{2} \d{1,2}, \d{4}) \(Week (?P<n>\d{1,2})\)$")


def parse_week(label: str) -> tuple[date, date, int]:
    """(Monday, Sunday, week number) from an export label; fails loudly on anything that is not a Monday-to-Sunday ISO week."""
    m = _WEEK.match(label)
    if not m:
        raise ValueError(f"unrecognised week label: {label!r}")
    start = datetime.strptime(m["a"], "%b %d, %Y").date()
    end = datetime.strptime(m["b"], "%b %d, %Y").date()
    n = int(m["n"])
    if start.weekday() != 0 or end - start != timedelta(days=6):
        raise ValueError(f"not a Monday-to-Sunday week: {label!r}")
    if start.isocalendar().week != n:
        raise ValueError(f"week number {n} is not the ISO week of {start}: {label!r}")
    return start, end, n


def election_week_start(year: int) -> date:
    d = ELECTION_DATES[year]
    return d - timedelta(days=d.weekday())


def weeks_to_election(week_start: date, year: int) -> int:
    """0 = the week containing election day, 1 = the week before, -1 = the week after."""
    return (election_week_start(year) - week_start).days // 7


def load_file(path: Path) -> pd.DataFrame:
    """One export, validated, one row per week."""
    m = _FILE.match(Path(path).name)
    if not m or m["seat"] not in SEATS:
        raise ValueError(f"file name must be <seat>_<year>_<channel>.csv with a known seat: {Path(path).name}")
    year = int(m["year"])
    if year not in ELECTION_DATES:
        raise ValueError(f"no election date for {year}: {Path(path).name}")
    raw = pd.read_csv(path)
    if list(raw.columns) != COLUMNS:
        raise ValueError(f"{Path(path).name}: columns are {list(raw.columns)}, expected {COLUMNS}")
    if raw.isna().any().any():
        raise ValueError(f"{Path(path).name}: missing values")
    weeks = [parse_week(x) for x in raw["Contact Week"]]
    out = pd.DataFrame({
        "seat": SEATS[m["seat"]], "year": year, "channel": m["channel"],
        "week_start": [w[0] for w in weeks], "week_end": [w[1] for w in weeks], "week_no": [w[2] for w in weeks],
        "attempts": raw.Attempts.astype(int), "contacts": raw.Contacts.astype(int),
        "meaningful": raw["Meaningful Interactions"].astype(int),
    })
    where = f"{Path(path).name}: "
    if out.week_start.duplicated().any():
        raise ValueError(where + "a week appears twice")
    if (out.week_start.map(lambda d: d.year) != year).any():
        raise ValueError(where + f"a week starts outside {year}")
    if ((out[["attempts", "contacts", "meaningful"]] < 0).any().any()
            or (out.contacts > out.attempts).any() or (out.meaningful > out.contacts).any()):
        raise ValueError(where + "need 0 <= meaningful <= contacts <= attempts in every week")
    contact_rate = (out.contacts / out.attempts).where(out.attempts > 0)
    if ((contact_rate - raw["Contact %"]).abs() > 1e-9).any():
        raise ValueError(where + "Contact % does not equal contacts / attempts")
    mi_rate = (out.meaningful / out.contacts).where(out.contacts > 0)
    if ((mi_rate - raw["MI %"]).abs().dropna() > 1e-9).any():
        raise ValueError(where + "MI % does not equal meaningful interactions / contacts")
    out["weeks_to_election"] = [weeks_to_election(d, year) for d in out.week_start]
    return out.sort_values("week_start", ascending=False).reset_index(drop=True)


def load_all(raw_dir: Path = RAW, through_election: bool = True) -> pd.DataFrame:
    """All seats, years and channels in one table. By default rows after election week are dropped."""
    files = sorted(Path(raw_dir).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"no campaign exports in {raw_dir}")
    out = pd.concat([load_file(f) for f in files], ignore_index=True)
    if through_election:
        out = out[out.weeks_to_election >= 0].reset_index(drop=True)
    expected = {(s, y, c) for s in SEATS.values() for y in ELECTION_DATES for c in CHANNELS}
    got = set(map(tuple, out[["seat", "year", "channel"]].drop_duplicates().to_numpy()))
    if got != expected:
        raise ValueError(f"missing or unexpected exports: {sorted(expected ^ got)}")
    return out


def summarize(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Totals and rates over the groups in `by`. Rates are None where the denominator is zero."""
    t = df.groupby(by)[["attempts", "contacts", "meaningful"]].sum()
    t["contact_rate"] = (t.contacts / t.attempts).where(t.attempts > 0)
    t["meaningful_rate"] = (t.meaningful / t.contacts).where(t.contacts > 0)
    return t
