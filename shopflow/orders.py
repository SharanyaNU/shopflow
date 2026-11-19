"""Orders: a customer buys some products, optionally with a coupon. Placing an order takes the items from stock,
charges the discounted total and awards loyalty points for it."""
import sqlite3

from shopflow import catalog, coupons, customers, inventory, loyalty, pricing
from shopflow.errors import Invalid, NotFound


def _wanted(items: list[dict]) -> dict[int, int]:
    """product id -> quantity; the same product twice in one order is one line."""
    if not items:
        raise Invalid("An order needs at least one item")
    wanted: dict[int, int] = {}
    for item in items:
        if item["quantity"] < 1:
            raise Invalid("Quantities must be at least 1")
        wanted[item["product_id"]] = wanted.get(item["product_id"], 0) + item["quantity"]
    return wanted


def place(conn: sqlite3.Connection, customer_id: int, items: list[dict], coupon_code: str | None = None) -> dict:
    """items: [{"product_id", "quantity"}]."""
    customers.get_customer(conn, customer_id)
    wanted = _wanted(items)
    products = {}
    for product_id in wanted:
        try:
            products[product_id] = catalog.get_product(conn, product_id)
        except NotFound:
            raise Invalid(f"Unknown product {product_id}") from None
    quote = pricing.quote(conn, [(products[p]["price_cents"], n) for p, n in wanted.items()], coupon_code)
    points = loyalty.points_for(quote.total_cents)
    order_id = conn.execute(
        "INSERT INTO orders (customer_id, status, subtotal_cents, discount_cents, total_cents, coupon_code, "
        "points_earned) VALUES (?, 'completed', ?, ?, ?, ?, ?)",
        (customer_id, quote.subtotal_cents, quote.discount_cents, quote.total_cents, quote.coupon_code, points),
    ).lastrowid
    for product_id, quantity in wanted.items():
        inventory.take(conn, product_id, quantity, order_id)
        conn.execute("INSERT INTO order_lines (order_id, product_id, quantity, unit_price_cents) VALUES (?, ?, ?, ?)",
                     (order_id, product_id, quantity, products[product_id]["price_cents"]))
    if quote.coupon_code:
        coupons.record_use(conn, quote.coupon_code)
    loyalty.award(conn, customer_id, points)
    return get_order(conn, order_id)


def get_order(conn: sqlite3.Connection, order_id: int) -> dict:
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise NotFound(f"Order {order_id} not found")
    order = dict(row)
    order["lines"] = [dict(r) for r in conn.execute(
        "SELECT l.id, l.product_id, p.name AS product_name, l.quantity, l.unit_price_cents, l.returned_quantity "
        "FROM order_lines l JOIN products p ON p.id = l.product_id WHERE l.order_id = ? ORDER BY l.id", (order_id,))]
    order["refunds"] = [dict(r) for r in conn.execute(
        "SELECT id, amount_cents, reason, created_at FROM refunds WHERE order_id = ? ORDER BY id", (order_id,))]
    order["refunded_cents"] = sum(r["amount_cents"] for r in order["refunds"])
    return order


def list_orders(conn: sqlite3.Connection, customer_id: int | None = None) -> list[dict]:
    sql = ("SELECT o.id, o.customer_id, c.name AS customer_name, o.status, o.total_cents, o.created_at "
           "FROM orders o JOIN customers c ON c.id = o.customer_id")
    args: tuple = ()
    if customer_id is not None:
        sql, args = sql + " WHERE o.customer_id = ?", (customer_id,)
    return [dict(r) for r in conn.execute(sql + " ORDER BY o.id DESC", args)]
