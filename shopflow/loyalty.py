"""Loyalty points: customers earn one point per whole dollar they pay, and lose them again when they get money
back."""
import sqlite3

POINTS_PER_DOLLAR = 1


def points_for(paid_cents: int) -> int:
    return paid_cents // 100 * POINTS_PER_DOLLAR


def award(conn: sqlite3.Connection, customer_id: int, points: int) -> None:
    conn.execute("UPDATE customers SET points = points + ? WHERE id = ?", (points, customer_id))


def revoke(conn: sqlite3.Connection, customer_id: int, points: int) -> None:
    """A balance never goes below zero."""
    conn.execute("UPDATE customers SET points = MAX(points - ?, 0) WHERE id = ?", (points, customer_id))
