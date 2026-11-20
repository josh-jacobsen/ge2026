"""Staging ETL for NZ general election results by voting place (2023 CSV, 2026 XLSX).

Produces long-format staging tables:

* ``stg_party_votes``      one row per (election, electorate, voting place, party)
* ``stg_candidate_votes``  one row per (election, electorate, voting place, candidate)
* ``stg_voting_places``    one row per (election, electorate, voting place)

``place_kind`` separates ordinary places from special/overseas/total rows so that the
two elections can be compared like-for-like (2026 is preliminary, ordinary votes only).
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
STAGING = ROOT / "data" / "staging"

# Non-party columns at the right-hand edge of every sheet.
TOTAL_COLS = {"Total Valid Party Votes", "Informal Party Votes", "Total Valid Candidate Votes", "Informal Candidate Votes"}

# Party names are spelled differently between elections; map to one canonical name.
PARTY_ALIASES = {
    "Animal Justice Party ": "Animal Justice Party",
    "Animal Justice Party Aotearoa New Zealand": "Animal Justice Party",
    "Opportunity Party": "The Opportunities Party (TOP)",
    "Conservative Party NZ": "New Conservatives",
}


def clean_party(name: str) -> str:
    name = " ".join(str(name).split())
    return PARTY_ALIASES.get(name, name)


def to_int(value) -> int | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if s == "":
        return None
    return int(float(s))


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()  # Māngere -> Mangere
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def classify(label: str, section: str) -> str:
    low = label.lower()
    if low.endswith("total"):
        return "total"
    if "votes allowed for party only" in low:
        return "party_only"
    if re.search(r"\btaken (in|for)\b", low) or "care home" in low or "hospital" in low or "defence force" in low:
        return "mobile_team"  # not a fixed, mappable location
    if "less than 6 votes" in low:
        return "suppressed"
    if "overseas" in low:
        return "overseas"
    if "special votes" in low:
        return "special"
    return "advance" if section == "advance" else "election_day"


def split_place(text: str) -> tuple[str, str, str]:
    """'Suburb, Venue, 12 Some Street' -> (suburb, venue, full text)."""
    parts = [p.strip() for p in text.split(",")]
    suburb = parts[0]
    venue = ", ".join(parts[1:]) if len(parts) > 1 else ""
    return suburb, venue, text.strip()


def _records(kind: str, header: list, rows: list[tuple[str, str, str]], election_year: int, electorate: str, electorate_no: str):
    """rows: (section, place_label, values-by-header-index)."""
    out = []
    for section, label, values in rows:
        place_kind = classify(label, section)
        suburb, venue, full = ("", label, label) if place_kind != "advance" and place_kind != "election_day" else split_place(label)
        for col, name in header:
            if name in TOTAL_COLS:
                continue
            votes = to_int(values[col]) if col < len(values) else None
            if votes is None:
                continue
            out.append(
                {
                    "election_year": election_year,
                    "electorate": electorate,
                    "electorate_no": electorate_no,
                    "voting_place_raw": full,
                    "suburb": suburb,
                    "venue": venue,
                    "section": section,
                    "place_kind": place_kind,
                    ("party" if kind == "party" else "candidate"): clean_party(name) if kind == "party" else " ".join(name.split()),
                    "votes": votes,
                }
            )
    return out


# --------------------------------------------------------------------------- 2023 (CSV)
def parse_2023(path: Path, kind: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    m = re.match(r"(.+?)\s+(\d+),", f"{rows[1][0]},")
    electorate, electorate_no = m.group(1).strip(), m.group(2)
    header = [(i, v.strip()) for i, v in enumerate(rows[2]) if i >= 2 and v.strip()]

    section, suburb, parsed = "advance", "", []
    for r in rows[3:]:
        if not any(c.strip() for c in r):
            continue
        first = r[0].strip()
        if first.startswith("Electorate Candidate Valid Votes") or first.startswith("Electorate Party Valid Votes"):
            break  # trailing candidate/party summary block
        if first.lower() == "advance voting places":
            section = "advance"
            continue
        if first.lower() == "voting places":
            section, suburb = "election_day", ""
            continue
        venue = r[1].strip() if len(r) > 1 else ""
        if venue.startswith("Valid "):
            continue  # 'Valid ... plus Informal ...' check row
        if not venue:
            continue
        if first:
            suburb = first
        kind_ = classify(venue, section)
        # mobile teams sit under a "Taken in <electorate>" heading that distinguishes identical team names
        label = f"{suburb}, {venue}" if kind_ in {"advance", "election_day", "mobile_team"} else venue
        parsed.append((section, label, r))
    return _records(kind, header, parsed, 2023, electorate, electorate_no)


# --------------------------------------------------------------------------- 2026 (XLSX)
def parse_2026(path: Path, kind: str) -> list[dict]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Party" if kind == "party" else "Candidate"]
    rows = list(ws.iter_rows(values_only=True))
    title = str(rows[0][0]).splitlines()[0]
    m = re.match(r"(\d+)\s+(.+?)\s+-\s+", title)
    electorate_no, electorate = m.group(1), m.group(2).strip()
    header = [(i, str(v).strip()) for i, v in enumerate(rows[0]) if i >= 1 and v and str(v).strip()]

    section, parsed = "advance", []
    for r in rows[1:]:
        label = (r[0] or "").strip() if isinstance(r[0], str) else ""
        if not label or label.startswith(("Source:", "Note:")):
            continue
        if label.upper() == "ADVANCE VOTING PLACES":
            section = "advance"
            continue
        if label.upper() == "VOTING PLACES":
            section = "election_day"
            continue
        parsed.append((section, label, r))
    return _records(kind, header, parsed, 2026, electorate, electorate_no)


def csv_kind(path: Path) -> str | None:
    """'party' or 'candidate', read from line 2 of the file ('<Electorate> N,Party Vote Details')."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [next(csv.reader([line]), []) for _, line in zip(range(2), fh)]
    text = ",".join(rows[1]) if len(rows) > 1 else ""
    if "Party Vote Details" in text:
        return "party"
    if "Candidate Vote Details" in text:
        return "candidate"
    return None


def csv_files(year: int, kind: str) -> list[Path]:
    """All CSVs under data/raw/ge<year>/ (any filename, any subfolder) of the given kind, by content."""
    root = RAW / f"ge{year}"
    files = sorted(p for p in root.rglob("*.csv") if not any(part.startswith("_") for part in p.relative_to(root).parts))
    return [p for p in files if csv_kind(p) == kind]


def electorate_of_csv(path: Path) -> str:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        line2 = next(csv.reader([list(fh)[1]]))[0]
    return re.match(r"(.+?)\s+\d+$", line2.strip()).group(1).strip()


def electorate_of_xlsx(path: Path) -> str | None:
    """Electorate name from the title cell of the 'Party' sheet ('31 North Shore - Party Vote Details ...')."""
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if "Party" not in wb.sheetnames or "Candidate" not in wb.sheetnames:
            return None
        title = str(next(wb["Party"].iter_rows(max_row=1, values_only=True))[0]).splitlines()[0]
        wb.close()
    except Exception:
        return None
    m = re.match(r"\d+\s+(.+?)\s+-\s+", title)
    return m.group(1).strip() if m else None


def _hidden(path: Path, base: Path) -> bool:
    return any(part.startswith("_") for part in path.relative_to(base).parts)


def raw_files(year: int) -> list[tuple[Path, Path]]:
    """(current path, canonical path) for every result file of the year, read from contents.

    2023: CSV, one per electorate and kind  -> ge2023_<electorate>_<party|candidate>.csv
    2026: XLSX, both sheets in one file    -> ge2026_<electorate>.xlsx
    Anything under an underscore-prefixed folder (_duplicates) or not recognisable is ignored.
    """
    base = RAW / f"ge{year}"
    out = []
    if year == 2023:
        for p in sorted(base.rglob("*.csv")):
            if not _hidden(p, base) and (kind := csv_kind(p)):
                out.append((p, base / f"ge2023_{slug(electorate_of_csv(p))}_{kind}.csv"))
    else:
        for p in sorted(base.rglob("*.xlsx")):
            if not _hidden(p, base) and not p.name.startswith("~$") and (name := electorate_of_xlsx(p)):
                out.append((p, base / f"ge2026_{slug(name)}.xlsx"))
    return out


def rename_raw(year: int, dry_run: bool = False) -> list[tuple[Path, Path]]:
    """Rename result files to canonical names from their contents and park identical duplicates.

    Safe to re-run. Two files with the same canonical name must be byte-identical (the extra goes to
    _duplicates/); otherwise it stops. Nothing is overwritten or deleted.
    """
    base = RAW / f"ge{year}"
    plan: dict[Path, Path] = {}
    extras: list[Path] = []
    # files that already carry their canonical name win, so re-runs are stable
    for p, target in sorted(raw_files(year), key=lambda x: (x[0] != x[1], x[0])):
        if target in plan.values():
            other = next(k for k, v in plan.items() if v == target)
            if other.read_bytes() != p.read_bytes():
                raise ValueError(f"{p} and {other} are both {target.name} but differ")
            extras.append(p)
            continue
        plan[p] = target
    moves = [(src, dst) for src, dst in plan.items() if src != dst]
    for src, dst in moves:
        if dst.exists() and dst not in plan:  # an unrelated file already has that name
            raise ValueError(f"refusing to overwrite {dst}")
    if not dry_run:
        tmp = [(src, src.with_name(src.name + ".renaming"), dst) for src, dst in moves]
        for src, mid, _ in tmp:  # two phases so swaps/chains cannot clobber each other
            src.rename(mid)
        for _, mid, dst in tmp:
            mid.rename(dst)
    dup_dir = base / "_duplicates"
    for p in extras:
        print(f"{'would move' if dry_run else 'moved'} identical duplicate: {p.relative_to(base)} -> _duplicates/")
        if not dry_run:
            dup_dir.mkdir(exist_ok=True)
            dest = dup_dir / p.name
            if dest.exists() and dest.read_bytes() != p.read_bytes():
                dest = dup_dir / f"{len(list(dup_dir.iterdir()))}_{p.name}"
            p.replace(dest)
    for src, dst in moves:
        print(f"{'would rename' if dry_run else 'renamed'}: {src.relative_to(base)} -> {dst.name}")
    return moves


def rename_raw_2023(dry_run: bool = False) -> list[tuple[Path, Path]]:
    return rename_raw(2023, dry_run)


def candidate_parties_2023() -> pd.DataFrame:
    """Candidate -> party from the summary block at the foot of each 2023 candidate file."""
    out = []
    for p in csv_files(2023, "candidate"):
        with open(p, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        electorate = re.match(r"(.+?)\s+\d+,", f"{rows[1][0]},").group(1).strip()
        start = next(i for i, r in enumerate(rows) if r and r[0].startswith("Electorate Candidate Valid Votes"))
        for r in rows[start + 1 :]:
            if len(r) >= 3 and r[0].strip() and r[1].strip():
                out.append({"election_year": 2023, "electorate": electorate, "candidate": " ".join(r[0].split()),
                            "party": clean_party(r[1]), "votes": to_int(r[2])})
    return pd.DataFrame(out)


def build() -> dict[str, pd.DataFrame]:
    party, cand = [], []
    for p in csv_files(2023, "party"):
        party += parse_2023(p, "party")
    for p in csv_files(2023, "candidate"):
        cand += parse_2023(p, "candidate")
    for p, _ in raw_files(2026):
        party += parse_2026(p, "party")
        cand += parse_2026(p, "candidate")

    stg_party, stg_cand = pd.DataFrame(party), pd.DataFrame(cand)
    for label, df in (("party", stg_party), ("candidate", stg_cand)):
        dup = df.duplicated(["election_year", "electorate", "section", "voting_place_raw", label])
        if dup.any():
            bad = df[dup][["election_year", "electorate"]].drop_duplicates().values.tolist()
            raise ValueError(f"duplicate {label} rows (same electorate loaded twice?): {bad}")
    for df in (stg_party, stg_cand):
        df["voting_place_id"] = (
            df["election_year"].astype(str) + "|" + df["electorate"].map(slug) + "|" + df["section"] + "|" + df["voting_place_raw"].map(slug)
        )

    place_cols = ["voting_place_id", "election_year", "electorate", "electorate_no", "voting_place_raw", "suburb", "venue", "section", "place_kind"]
    stg_places = stg_party[place_cols].drop_duplicates().reset_index(drop=True)
    return {
        "stg_party_votes": stg_party,
        "stg_candidate_votes": stg_cand,
        "stg_voting_places": stg_places,
        "stg_candidate_party": candidate_parties_2023(),
    }


def checks(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Sum of place rows vs the official 'Total' row, per election/electorate/table."""
    rows = []
    for name in ("stg_party_votes", "stg_candidate_votes"):
        df = tables[name]
        by = df.groupby(["election_year", "electorate", "place_kind"])["votes"].sum().unstack(fill_value=0)
        by["places_sum"] = by.drop(columns="total").sum(axis=1)
        by["diff"] = by["places_sum"] - by["total"]
        by.insert(0, "table", name)
        rows.append(by.reset_index())
    return pd.concat(rows, ignore_index=True)


def write(tables: dict[str, pd.DataFrame]) -> None:
    STAGING.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(STAGING / f"{name}.parquet", index=False)
        df.to_csv(STAGING / f"{name}.csv", index=False)


if __name__ == "__main__":
    import sys

    if "--rename-only" in sys.argv:
        for y in (2023, 2026):
            rename_raw(y, dry_run="--dry-run" in sys.argv)
        raise SystemExit
    t = build()
    write(t)
    for k, v in t.items():
        print(k, v.shape)
    print(checks(t).to_string())
