"""Stock: how many of each product are on the shelf, how many of those are reserved for orders that haven't shipped,
and every change to the shelf (the stock movements)."""
import sqlite3

from shopflow.errors import Conflict, NotFound


def available_of(product: sqlite3.Row | dict) -> int:
    """How many can still be sold: on the shelf, minus what open orders have reserved."""
    return product["on_hand"] - product["reserved"]


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


def reserve(conn: sqlite3.Connection, product_id: int, quantity: int, order_id: int) -> None:
    """Hold items for a placed order; they stay on the shelf until it ships."""
    product = _product(conn, product_id)
    if available_of(product) < quantity:
        raise Conflict(f"Only {available_of(product)} of {product['name']} in stock")
    conn.execute("UPDATE products SET reserved = reserved + ? WHERE id = ?", (quantity, product_id))


def release(conn: sqlite3.Connection, product_id: int, quantity: int, order_id: int) -> None:
    """A cancelled order's reservation ends; the items are available again."""
    conn.execute("UPDATE products SET reserved = reserved - ? WHERE id = ?", (quantity, product_id))


def ship(conn: sqlite3.Connection, product_id: int, quantity: int, order_id: int) -> None:
    """Reserved items leave the shelf."""
    conn.execute("UPDATE products SET on_hand = on_hand - ?, reserved = reserved - ? WHERE id = ?",
                 (quantity, quantity, product_id))
    _move(conn, product_id, -quantity, "shipped", order_id)


def put_back(conn: sqlite3.Connection, product_id: int, quantity: int, order_id: int) -> None:
    """Returned items go back on the shelf."""
    _product(conn, product_id)
    conn.execute("UPDATE products SET on_hand = on_hand + ? WHERE id = ?", (quantity, product_id))
    _move(conn, product_id, quantity, "return", order_id)


def movements(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute("SELECT change, reason, order_id, created_at FROM stock_movements WHERE product_id = ? "
                        "ORDER BY id", (product_id,)).fetchall()
    return [dict(r) for r in rows]
