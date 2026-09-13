"""Money is stored as integer minor units (1/100 of the currency unit).

Example: 15_000.00 UZS = 1_500_000 minor units (tiyin-equivalent).
Never use float for money.
"""

from decimal import Decimal, ROUND_HALF_UP


MINOR_FACTOR = 100


def to_minor(amount: Decimal | int | str) -> int:
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(value * MINOR_FACTOR)


def from_minor(amount_minor: int) -> Decimal:
    return (Decimal(amount_minor) / MINOR_FACTOR).quantize(Decimal("0.01"))
