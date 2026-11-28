import pandas as pd
import pytest

import vote_scope


def _staging(tmp_path, rows):
    pd.DataFrame(rows, columns=["election_year", "count_stage", "place_kind", "votes"]).to_parquet(tmp_path / "stg_party_votes.parquet")
    return tmp_path


BASE = [
    (2023, "final", "advance", 10), (2023, "final", "special", 4), (2023, "final", "total", 14),
    (2026, "preliminary", "advance", 11), (2026, "preliminary", "election_day", 5), (2026, "preliminary", "total", 16),
]


def test_ordinary_keeps_only_advance_and_election_day(tmp_path):
    df = vote_scope.load(scope="ordinary", staging=_staging(tmp_path, BASE))
    assert set(df.place_kind) == {"advance", "election_day"}
    assert df.votes.sum() == 10 + 11 + 5


def test_all_refuses_when_special_votes_are_missing_for_a_year(tmp_path):
    with pytest.raises(ValueError, match="2026"):
        vote_scope.load(scope="all", staging=_staging(tmp_path, BASE))


def test_all_includes_special_but_never_the_total_rows(tmp_path):
    rows = BASE + [(2026, "preliminary", "special", 3)]
    df = vote_scope.load(scope="all", staging=_staging(tmp_path, rows))
    assert "total" not in set(df.place_kind)
    assert df[df.election_year == 2026].votes.sum() == 11 + 5 + 3


def test_stage_selects_the_2026_count_and_never_double_counts(tmp_path):
    rows = BASE + [(2026, "final", "advance", 20), (2026, "final", "special", 7)]
    staging = _staging(tmp_path, rows)
    prelim = vote_scope.load(scope="ordinary", stage="preliminary", staging=staging)
    final = vote_scope.load(scope="ordinary", stage="final", staging=staging)
    assert prelim[prelim.election_year == 2026].votes.sum() == 16
    assert final[final.election_year == 2026].votes.sum() == 20
    assert (final.election_year == 2023).sum() == (prelim.election_year == 2023).sum()   # 2023 always included


def test_missing_final_stage_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="final"):
        vote_scope.load(stage="final", staging=_staging(tmp_path, BASE))


def test_unknown_scope_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="scope"):
        vote_scope.load(scope="everything", staging=_staging(tmp_path, BASE))


def test_old_staging_without_count_stage_is_rejected(tmp_path):
    pd.DataFrame({"election_year": [2023], "place_kind": ["advance"], "votes": [1]}).to_parquet(tmp_path / "stg_party_votes.parquet")
    with pytest.raises(ValueError, match="count_stage"):
        vote_scope.load(staging=tmp_path)


def test_final_electorate_totals_serve_scope_all_only(tmp_path):
    rows = BASE + [(2026, "final", "electorate_total", 40)]
    staging = _staging(tmp_path, rows)
    df = vote_scope.load(scope="all", stage="final", staging=staging)
    assert df[df.election_year == 2026].votes.sum() == 40          # the electorate total, not the preliminary rows
    assert df[df.election_year == 2023].votes.sum() == 10 + 4      # 2023: every non-total row
    with pytest.raises(ValueError, match="no ordinary-vote rows for 2026 final"):
        vote_scope.load(scope="ordinary", stage="final", staging=staging)
