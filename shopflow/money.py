"""Money is kept as whole cents everywhere; these helpers format it and take percentages of it."""


def fmt(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def percent_of(cents: int, percent: int) -> int:
    """`percent` % of an amount, rounded down to a whole cent (the shop never gives away a fraction of a cent)."""
    return cents * percent // 100
