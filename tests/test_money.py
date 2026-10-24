from decimal import Decimal

import pytest

from app.services.money import percent_of, rub, stars_for


@pytest.mark.parametrize(("kop", "text"), [(0, "0 ₽"), (15000, "150 ₽"), (15050, "150,50 ₽")])
def test_rub(kop: int, text: str) -> None:
    assert rub(kop) == text


@pytest.mark.parametrize(
    ("kop", "rate", "stars"),
    [(0, "1.5", 0), (15000, "1.5", 100), (15001, "1.5", 101), (50, "1.5", 1), (19900, "1.8", 111)],
)
def test_stars_round_up(kop: int, rate: str, stars: int) -> None:
    assert stars_for(kop, Decimal(rate)) == stars


def test_percent_rounds_down() -> None:
    assert percent_of(999, 10) == 99
