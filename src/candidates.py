"""Candidate names as the Commission prints them ("SURNAME, Given names") turned into display names ("Given names Surname")."""

from __future__ import annotations

import re

_MC = re.compile(r"^(Mc|Mac)([A-Z]{2,})$")


def _surname_word(word: str) -> str:
    m = _MC.match(word)
    if m:                                    # McCABE -> McCabe, but MACKAY (no lower-case prefix) -> Mackay
        return m[1] + m[2].capitalize()
    return word.capitalize()


def display_name(candidate: str) -> str:
    """'SWARBRICK, Chlöe' -> 'Chlöe Swarbrick'; 'McCABE, Phil' -> 'Phil McCabe'; 'TE AU-SKIPWORTH, Heather' -> 'Heather Te Au-Skipworth'."""
    if "," not in candidate:
        raise ValueError(f"expected 'SURNAME, Given names': {candidate!r}")
    surname, given = (p.strip() for p in candidate.split(",", 1))
    if not surname or not given:
        raise ValueError(f"expected 'SURNAME, Given names': {candidate!r}")
    parts = re.split(r"([ '\-])", surname)   # keep the separators
    surname = "".join(p if p in {" ", "'", "-"} else _surname_word(p) for p in parts)
    return f"{given} {surname}"
