from decimal import ROUND_CEILING, Decimal


def rub(kop: int) -> str:
    """Сумма для показа: 150 ₽ или 150,50 ₽."""
    rubles, kopecks = divmod(kop, 100)
    return f"{rubles} ₽" if kopecks == 0 else f"{rubles},{kopecks:02d} ₽"


def stars_for(kop: int, rub_per_star: Decimal) -> int:
    """Сколько звёзд выставить за сумму в копейках. Округляем вверх, минимум одна."""
    if kop <= 0:
        return 0
    stars = (Decimal(kop) / 100 / rub_per_star).to_integral_value(rounding=ROUND_CEILING)
    return max(int(stars), 1)


def percent_of(kop: int, percent: int) -> int:
    """Процент от суммы, с округлением вниз до копейки."""
    return kop * percent // 100
