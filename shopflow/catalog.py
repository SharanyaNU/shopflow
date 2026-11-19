"""Products: what the shop sells and at what price."""
import sqlite3

from shopflow import inventory
from shopflow.errors import Conflict, Invalid, NotFound

PER_PAGE = 5


def _out(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "sku": row["sku"], "name": row["name"], "price_cents": row["price_cents"],
            "on_hand": row["on_hand"], "reserved": row["reserved"], "available": inventory.available_of(row)}


def list_products(conn: sqlite3.Connection) -> list[dict]:
    return [_out(r) for r in conn.execute("SELECT * FROM products ORDER BY name, id").fetchall()]


def search(products: list[dict], q: str) -> list[dict]:
    """Products whose name or SKU contains the search text, ignoring case."""
    q = q.strip()
    return [p for p in products if q in p["name"] or q in p["sku"]] if q else products


def page_of(items: list[dict], page: int, per_page: int = PER_PAGE) -> tuple[list[dict], int]:
    """One page of the items (pages start at 1) and how many pages there are."""
    pages = max(1, -(-len(items) // per_page))
    start = (max(page, 1) - 1) * per_page
    return items[start:start + per_page - 1], pages


def get_product(conn: sqlite3.Connection, product_id: int) -> dict:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise NotFound(f"Product {product_id} not found")
    return _out(row)


def create_product(conn: sqlite3.Connection, sku: str, name: str, price_cents: int, on_hand: int = 0) -> dict:
    """SKUs are stored in upper case and are unique."""
    sku, name = sku.strip().upper(), name.strip()
    if not sku or not name:
        raise Invalid("A product needs a SKU and a name")
    if price_cents < 0 or on_hand < 0:
        raise Invalid("Price and stock can't be negative")
    if conn.execute("SELECT 1 FROM products WHERE sku = ?", (sku,)).fetchone():
        raise Conflict(f"SKU {sku} already exists")
    product_id = conn.execute("INSERT INTO products (sku, name, price_cents, on_hand) VALUES (?, ?, ?, 0)",
                              (sku, name, price_cents)).lastrowid
    if on_hand:
        inventory.receive(conn, product_id, on_hand, "initial stock")
    return get_product(conn, product_id)
