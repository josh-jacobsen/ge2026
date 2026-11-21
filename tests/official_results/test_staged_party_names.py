"""Staged data uses the canonical party names (needs data/raw; see unit/test_party_names.py for the decisions)."""


def test_staged_parties_use_canonical_names(party_votes):
    parties = set(party_votes.party)
    assert "Conservative Party NZ" not in parties
    assert "Opportunity Party" not in parties
    assert not any(p != " ".join(p.split()) for p in parties), "party names must be whitespace-normalised"
