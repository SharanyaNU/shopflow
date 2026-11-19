"""Demo data for a new, empty database, so the pages have something to show. SHOPFLOW_SEED=0 turns it off."""
import os

from shopflow import catalog, coupons, customers, db, orders, returns

PRODUCTS = [
    ("LAMP-01", "Desk lamp", 2499, 12),
    ("CHAIR-01", "Office chair", 14900, 5),
    ("NOTE-A5", "A5 notebook", 450, 80),
    ("PEN-BLK", "Black gel pen", 199, 200),
    ("MUG-01", "Coffee mug", 1200, 30),
    ("BAG-01", "Laptop bag", 5999, 8),
    ("STAND-01", "Monitor stand", 3999, 6),
    ("CABLE-C", "USB-C cable", 1299, 40),
]
CUSTOMERS = [("Asha Rao", "asha@example.com"), ("Ben Ortiz", "ben@example.com"), ("Chen Li", "chen@example.com")]


def seed_if_empty() -> None:
    if os.getenv("SHOPFLOW_SEED", "1") == "0":
        return
    with db.transaction() as conn:
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
            return
        product = [catalog.create_product(conn, *p)["id"] for p in PRODUCTS]
        customer = [customers.create_customer(conn, *c)["id"] for c in CUSTOMERS]
        coupons.create_coupon(conn, "WELCOME10", "percent", 10)
        coupons.create_coupon(conn, "TENOFF", "fixed", 1000, min_subtotal_cents=5000)
        first = orders.place(conn, customer[0], [{"product_id": product[0], "quantity": 2},
                                                 {"product_id": product[2], "quantity": 3}], "WELCOME10")
        orders.place(conn, customer[1], [{"product_id": product[1], "quantity": 1}])
        returns.return_items(conn, first["id"], [{"line_id": first["lines"][0]["id"], "quantity": 1}],
                             "Arrived broken")
