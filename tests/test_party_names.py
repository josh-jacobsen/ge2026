"""Party-name decisions that change swing numbers. Change deliberately, not by accident."""

import etl


def test_conservatives_are_one_party_across_elections():
    # Confirmed by the project owner: "Conservative Party NZ" (2026) is the same party as "New Conservatives" (2023)
    assert etl.clean_party("Conservative Party NZ") == etl.clean_party("New Conservatives") == "New Conservatives"


def test_opportunity_party_is_top():
    assert etl.clean_party("Opportunity Party") == etl.clean_party("The Opportunities Party (TOP)")


def test_animal_justice_spellings_are_one_party():
    assert etl.clean_party("Animal Justice Party Aotearoa New Zealand") == etl.clean_party("Animal Justice Party ")


def test_staged_parties_use_canonical_names(party_votes):
    parties = set(party_votes.party)
    assert "Conservative Party NZ" not in parties
    assert "Opportunity Party" not in parties
    assert not any(p != " ".join(p.split()) for p in parties), "party names must be whitespace-normalised"
