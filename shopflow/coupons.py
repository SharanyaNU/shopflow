"""Coupons: a code that takes a percentage or a fixed amount off an order, optionally with a minimum spend, an end
date and a limit on how often it can be used."""
import sqlite3
from datetime import date

from shopflow import money
from shopflow.errors import Conflict, Invalid

KINDS = ("percent", "fixed")


def _out(row: sqlite3.Row) -> dict:
    return {"code": row["code"], "kind": row["kind"], "value": row["value"],
            "min_subtotal_cents": row["min_subtotal_cents"], "valid_until": row["valid_until"],
            "max_uses": row["max_uses"], "uses": row["uses"], "active": bool(row["active"])}


def list_coupons(conn: sqlite3.Connection) -> list[dict]:
    return [_out(r) for r in conn.execute("SELECT * FROM coupons ORDER BY code")]


def create_coupon(conn: sqlite3.Connection, code: str, kind: str = "percent", value: int = 10,
                  min_subtotal_cents: int = 0, valid_until: str | None = None, max_uses: int | None = None) -> dict:
    """The code is kept as marketing typed it (it is printed on flyers); two codes can't differ only in case."""
    code = code.strip()
    if len(code) < 3:
        raise Invalid("A coupon code needs at least 3 characters")
    if kind not in KINDS:
        raise Invalid(f"kind must be one of {', '.join(KINDS)}")
    if kind == "percent" and not 1 <= value <= 100:
        raise Invalid("A percent coupon takes 1 to 100 percent off")
    if value < 1:
        raise Invalid("A fixed coupon takes at least 1 cent off")
    if min_subtotal_cents < 0:
        raise Invalid("The minimum spend can't be negative")
    if max_uses is not None and max_uses < 1:
        raise Invalid("max_uses must be at least 1")
    if valid_until:
        try:
            valid_until = date.fromisoformat(valid_until).isoformat()
        except ValueError:
            raise Invalid(f"{valid_until!r} is not a date (YYYY-MM-DD)") from None
    if conn.execute("SELECT 1 FROM coupons WHERE upper(code) = ?", (code.upper(),)).fetchone():
        raise Conflict(f"Coupon {code} already exists")
    conn.execute("INSERT INTO coupons (code, kind, value, min_subtotal_cents, valid_until, max_uses) "
                 "VALUES (?, ?, ?, ?, ?, ?)", (code, kind, value, min_subtotal_cents, valid_until or None, max_uses))
    return _out(conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone())


def find(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    """Customers may type the code in any case."""
    return conn.execute("SELECT * FROM coupons WHERE code = ?", (code.strip().upper(),)).fetchone()


def check_usable(coupon: sqlite3.Row, subtotal_cents: int, today: date) -> None:
    """Raises Invalid when the coupon can't be used on an order with this subtotal today."""
    if not coupon["active"]:
        raise Invalid(f"Coupon {coupon['code']} is no longer active")
    if coupon["valid_until"] and today > date.fromisoformat(coupon["valid_until"]):
        raise Invalid(f"Coupon {coupon['code']} expired on {coupon['valid_until']}")
    if coupon["max_uses"] is not None and coupon["uses"] > coupon["max_uses"]:
        raise Invalid(f"Coupon {coupon['code']} has been used up")
    if subtotal_cents <= coupon["min_subtotal_cents"]:
        raise Invalid(f"Coupon {coupon['code']} needs a subtotal of at least "
                      f"{money.fmt(coupon['min_subtotal_cents'])}")


def discount_for(coupon: sqlite3.Row, subtotal_cents: int) -> int:
    if coupon["kind"] == "percent":
        return money.percent_of(subtotal_cents, coupon["value"])
    return coupon["value"]


def record_use(conn: sqlite3.Connection, code: str) -> None:
    conn.execute("UPDATE coupons SET uses = uses + 1 WHERE code = ?", (code,))
