"""SQLite storage. The database file is created on first start; SHOPFLOW_DB points it elsewhere (the tests use a
temporary file)."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "instance" / "shopflow.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY,
    sku         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    on_hand     INTEGER NOT NULL DEFAULT 0 CHECK (on_hand >= 0),
    reserved    INTEGER NOT NULL DEFAULT 0 CHECK (reserved >= 0)
);
CREATE TABLE IF NOT EXISTS stock_movements (
    id         INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    change     INTEGER NOT NULL,
    reason     TEXT NOT NULL,
    order_id   INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS customers (
    id     INTEGER PRIMARY KEY,
    name   TEXT NOT NULL,
    email  TEXT NOT NULL UNIQUE,
    points INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS coupons (
    code               TEXT PRIMARY KEY,
    kind               TEXT NOT NULL CHECK (kind IN ('percent', 'fixed')),
    value              INTEGER NOT NULL CHECK (value > 0),
    min_subtotal_cents INTEGER NOT NULL DEFAULT 0,
    valid_until        TEXT,
    max_uses           INTEGER,
    uses               INTEGER NOT NULL DEFAULT 0,
    active             INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL REFERENCES customers(id),
    status         TEXT NOT NULL,
    subtotal_cents INTEGER NOT NULL,
    discount_cents INTEGER NOT NULL DEFAULT 0,
    total_cents    INTEGER NOT NULL,
    coupon_code    TEXT,
    points_earned  INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS order_lines (
    id                INTEGER PRIMARY KEY,
    order_id          INTEGER NOT NULL REFERENCES orders(id),
    product_id        INTEGER NOT NULL REFERENCES products(id),
    quantity          INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents  INTEGER NOT NULL,
    returned_quantity INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS refunds (
    id           INTEGER PRIMARY KEY,
    order_id     INTEGER NOT NULL REFERENCES orders(id),
    amount_cents INTEGER NOT NULL,
    reason       TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def path() -> Path:
    return Path(os.getenv("SHOPFLOW_DB") or DEFAULT_PATH)


def connect() -> sqlite3.Connection:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction():
    """One connection for one unit of work: committed if it finishes, rolled back if it raises."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init() -> None:
    with transaction() as conn:
        conn.executescript(SCHEMA)
