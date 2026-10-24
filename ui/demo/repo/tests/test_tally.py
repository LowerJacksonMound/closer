import pytest

from tally import total, share, label


def test_total():
    assert total([1.25, 2.5]) == 3.75


def test_share():
    assert share(10, 4) == 2.5


def test_share_refuses_zero_people():
    with pytest.raises(ValueError):
        share(10, 0)


def test_label():
    assert label(3) == "$3.00"
