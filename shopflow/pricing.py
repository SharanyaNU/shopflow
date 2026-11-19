"""What an order costs: the items, minus the coupon's discount."""
import sqlite3
from dataclasses import dataclass

from shopflow import coupons, money
from shopflow.errors import Invalid


@dataclass
class Quote:
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    coupon_code: str | None


def quote(conn: sqlite3.Connection, lines: list[tuple[int, int]], coupon_code: str | None = None) -> Quote:
    """lines: (unit price in cents, quantity) per item."""
    subtotal = sum(unit * quantity for unit, quantity in lines)
    discount, code = 0, None
    if coupon_code:
        coupon = coupons.find_active(conn, coupon_code)
        if coupon is None:
            raise Invalid(f"Coupon {coupon_code!r} is not valid")
        discount, code = money.percent_of(subtotal, coupon["percent_off"]), coupon["code"]
    return Quote(subtotal, discount, subtotal - discount, code)
