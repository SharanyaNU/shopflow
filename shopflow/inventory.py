"""Stock: how many of each product are on the shelf, and every change to it (the stock movements)."""
import sqlite3

from shopflow.errors import Conflict, NotFound


def available_of(product: sqlite3.Row | dict) -> int:
    """How many can still be sold."""
    return product["on_hand"]


def _product(conn: sqlite3.Connection, product_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise NotFound(f"Product {product_id} not found")
    return row


def _move(conn: sqlite3.Connection, product_id: int, change: int, reason: str, order_id: int | None) -> None:
    conn.execute("INSERT INTO stock_movements (product_id, change, reason, order_id) VALUES (?, ?, ?, ?)",
                 (product_id, change, reason, order_id))


def receive(conn: sqlite3.Connection, product_id: int, quantity: int, reason: str = "received") -> None:
    """New stock arrives."""
    conn.execute("UPDATE products SET on_hand = on_hand + ? WHERE id = ?", (quantity, product_id))
    _move(conn, product_id, quantity, reason, None)


def take(conn: sqlite3.Connection, product_id: int, quantity: int, order_id: int) -> None:
    """Sold items leave the shelf."""
    product = _product(conn, product_id)
    if available_of(product) < quantity:
        raise Conflict(f"Only {available_of(product)} of {product['name']} in stock")
    conn.execute("UPDATE products SET on_hand = on_hand - ? WHERE id = ?", (quantity, product_id))
    _move(conn, product_id, -quantity, "sale", order_id)


def put_back(conn: sqlite3.Connection, product_id: int, quantity: int, order_id: int) -> None:
    """Returned items go back on the shelf."""
    _product(conn, product_id)
    conn.execute("UPDATE products SET on_hand = on_hand + ? WHERE id = ?", (quantity, product_id))
    _move(conn, product_id, quantity, "return", order_id)


def movements(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute("SELECT change, reason, order_id, created_at FROM stock_movements WHERE product_id = ? "
                        "ORDER BY id", (product_id,)).fetchall()
    return [dict(r) for r in rows]
