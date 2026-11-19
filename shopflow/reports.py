"""Sales figures for the catalogue: how many units of each product customers kept."""
import sqlite3

from shopflow import orders


def units_sold(conn: sqlite3.Connection, product_id: int) -> int:
    """Units of the product in orders that weren't cancelled, minus the units returned."""
    sold = 0
    for summary in orders.list_orders(conn):
        order = orders.get_order(conn, summary["id"])
        if order["status"] == "cancelled":
            continue
        for line in order["lines"]:
            if line["product_id"] == product_id:
                sold += line["quantity"] - line["returned_quantity"]
    return sold


def best_sellers(conn: sqlite3.Connection, products: list[dict], limit: int | None = None) -> list[dict]:
    """The products, most units sold first (then by name), each with its "units_sold"."""
    ranked = sorted(({**p, "units_sold": units_sold(conn, p["id"])} for p in products),
                    key=lambda p: (-p["units_sold"], p["name"]))
    return ranked[:limit] if limit else ranked
