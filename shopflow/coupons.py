"""Coupons: a code that takes a percentage off an order."""
import sqlite3

from shopflow.errors import Conflict, Invalid


def _out(row: sqlite3.Row) -> dict:
    return {"code": row["code"], "percent_off": row["percent_off"], "active": bool(row["active"])}


def list_coupons(conn: sqlite3.Connection) -> list[dict]:
    return [_out(r) for r in conn.execute("SELECT * FROM coupons ORDER BY code")]


def create_coupon(conn: sqlite3.Connection, code: str, percent_off: int) -> dict:
    """Codes are case-insensitive: they are stored and looked up in upper case."""
    code = code.strip().upper()
    if len(code) < 3:
        raise Invalid("A coupon code needs at least 3 characters")
    if not 1 <= percent_off <= 100:
        raise Invalid("percent_off must be between 1 and 100")
    if conn.execute("SELECT 1 FROM coupons WHERE code = ?", (code,)).fetchone():
        raise Conflict(f"Coupon {code} already exists")
    conn.execute("INSERT INTO coupons (code, percent_off) VALUES (?, ?)", (code, percent_off))
    return _out(conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone())


def find_active(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM coupons WHERE code = ? AND active = 1", (code.strip().upper(),)).fetchone()
