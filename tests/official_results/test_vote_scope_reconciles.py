"""Scope 'all' (every row except 'total') must equal the Commission's own electorate total, so that adding special
votes later cannot silently drop or double count anything."""

import pytest


@pytest.mark.parametrize("year,stage", [(2023, "final"), (2026, "preliminary")])
@pytest.mark.parametrize("table", ["stg_party_votes", "stg_candidate_votes"])
def test_every_row_but_total_equals_the_total_row(tables, year, stage, table):
    df = tables[table]
    df = df[(df.election_year == year) & (df.count_stage == stage)]
    by = df.groupby(["electorate", df.place_kind == "total"]).votes.sum().unstack()
    assert (by[False] == by[True]).all(), by[by[False] != by[True]]


def test_staging_rows_are_tagged_with_a_stage(tables):
    for name in ("stg_party_votes", "stg_candidate_votes", "stg_voting_places"):
        df = tables[name]
        assert set(df[df.election_year == 2023].count_stage) == {"final"}
        assert set(df[df.election_year == 2026].count_stage) <= {"preliminary", "final"}
