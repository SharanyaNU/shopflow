"""Customers and their loyalty points balance."""
import re
import sqlite3

from shopflow.errors import Conflict, Invalid, NotFound

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def list_customers(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT id, name, email, points FROM customers ORDER BY name, id")]


def get_customer(conn: sqlite3.Connection, customer_id: int) -> dict:
    row = conn.execute("SELECT id, name, email, points FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if row is None:
        raise NotFound(f"Customer {customer_id} not found")
    return dict(row)


def create_customer(conn: sqlite3.Connection, name: str, email: str) -> dict:
    """E-mail addresses are unique, compared without case."""
    name, email = name.strip(), email.strip().lower()
    if not name:
        raise Invalid("A customer needs a name")
    if not EMAIL.match(email):
        raise Invalid(f"{email!r} is not an e-mail address")
    if conn.execute("SELECT 1 FROM customers WHERE email = ?", (email,)).fetchone():
        raise Conflict(f"A customer with e-mail {email} already exists")
    customer_id = conn.execute("INSERT INTO customers (name, email) VALUES (?, ?)", (name, email)).lastrowid
    return get_customer(conn, customer_id)
