"""Returns: a customer sends back some items of an order. They go back into stock, the customer gets back what they
paid for them, and the loyalty points that money earned are taken back."""
import sqlite3

from shopflow import inventory, loyalty, orders
from shopflow.errors import Conflict, Invalid


def refund_for(order: dict, gross_cents: int) -> int:
    """What the customer paid for items worth `gross_cents` before the discount: a coupon's discount is shared across
    the order's items in proportion to their price, rounded down to a cent."""
    if order["subtotal_cents"] == 0:
        return 0
    return gross_cents * order["total_cents"] // order["subtotal_cents"]


def return_items(conn: sqlite3.Connection, order_id: int, items: list[dict], reason: str = "") -> dict:
    """items: [{"line_id", "quantity"}]. A line can't be returned more often than it was bought, and an order never
    refunds more than was paid for it."""
    order = orders.get_order(conn, order_id)
    if order["status"] == "cancelled":
        raise Conflict("A cancelled order can't be returned")
    if not items:
        raise Invalid("Say which items are returned")
    lines = {line["id"]: line for line in order["lines"]}
    wanted: dict[int, int] = {}
    for item in items:
        if item["line_id"] not in lines:
            raise Invalid(f"Line {item['line_id']} is not part of order {order_id}")
        if item["quantity"] < 1:
            raise Invalid("Quantities must be at least 1")
        wanted[item["line_id"]] = wanted.get(item["line_id"], 0) + item["quantity"]

    gross = 0
    for line_id, quantity in wanted.items():
        line = lines[line_id]
        left = line["quantity"] - line["returned_quantity"]
        if quantity > left:
            raise Conflict(f"Only {left} of {line['product_name']} can still be returned")
        conn.execute("UPDATE order_lines SET returned_quantity = returned_quantity + ? WHERE id = ?",
                     (quantity, line_id))
        inventory.put_back(conn, line["product_id"], quantity, order_id)
        gross += line["unit_price_cents"] * quantity

    amount = min(refund_for(order, gross), order["total_cents"] - order["refunded_cents"])
    refund_id = conn.execute("INSERT INTO refunds (order_id, amount_cents, reason) VALUES (?, ?, ?)",
                             (order_id, amount, reason.strip() or "returned items")).lastrowid
    loyalty.revoke(conn, order["customer_id"], loyalty.points_for(amount))
    return {"refund_id": refund_id, "order_id": order_id, "amount_cents": amount}
