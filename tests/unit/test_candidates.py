import pytest

import candidates


@pytest.mark.parametrize("raw, shown", [
    ("SWARBRICK, Chlöe", "Chlöe Swarbrick"),
    ("McCABE, Phil", "Phil McCabe"),
    ("McKEE, Abe", "Abe McKee"),
    ("O'CONNOR PATENA, George", "George O'Connor Patena"),
    ("TE AU-SKIPWORTH, Heather", "Heather Te Au-Skipworth"),
    ("DAO-MCLAY, Gina Quynh", "Gina Quynh Dao-Mclay"),
    ("COLLINS, Fa'anānā Efeso", "Fa'anānā Efeso Collins"),
    ("MACKAY, Jo", "Jo Mackay"),
])
def test_display_name(raw, shown):
    assert candidates.display_name(raw) == shown


@pytest.mark.parametrize("bad", ["Chlöe Swarbrick", ", Chlöe", "SWARBRICK,"])
def test_display_name_rejects_unexpected_formats(bad):
    with pytest.raises(ValueError):
        candidates.display_name(bad)
