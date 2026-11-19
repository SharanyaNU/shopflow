"""The back-office pages: plain HTML forms that call the same modules as the API."""
from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from shopflow import catalog, coupons, customers, db, inventory, orders, returns
from shopflow.errors import Conflict, Invalid, NotFound
from shopflow.money import fmt

STYLE = """
body { font-family: system-ui, sans-serif; margin: 0; color: #1d2733; background: #f7f6f2; }
header { background: #1d2733; padding: 12px 24px; }
header a { color: #f7f6f2; margin-right: 18px; text-decoration: none; font-weight: 600; }
main { padding: 24px; max-width: 980px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 24px; background: #fff; }
th, td { border: 1px solid #d9d5ca; padding: 6px 10px; text-align: left; }
form { background: #fff; border: 1px solid #d9d5ca; padding: 16px; margin: 12px 0 24px; }
label { display: block; margin: 8px 0 4px; }
.error { background: #f8e0dc; border: 1px solid #b83a1a; padding: 10px; margin: 12px 0; }
.status { font-weight: 600; }
"""


def page(title: str, body: str, error: str = "", status: int = 200) -> HTMLResponse:
    nav = "".join(f'<a href="{href}">{label}</a>' for href, label in (
        ("/", "Home"), ("/products", "Products"), ("/customers", "Customers"), ("/orders", "Orders"),
        ("/orders/new", "New order"), ("/coupons", "Coupons")))
    alert = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{escape(title)} · ShopFlow</title><style>{STYLE}</style></head>
<body><header><nav aria-label="Main">{nav}</nav></header><main><h1>{escape(title)}</h1>{alert}{body}</main></body></html>""",
                        status_code=status)


def not_found(message: str) -> HTMLResponse:
    return page("Not found", f"<p>{escape(message)}</p>", status=404)


async def form_data(request: Request) -> dict[str, str]:
    parsed = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    return {k: v[0].strip() for k, v in parsed.items()}


def to_cents(text: str) -> int:
    try:
        value = Decimal(text.replace("$", "").replace(",", ""))
    except InvalidOperation:
        raise Invalid(f"{text!r} is not a price") from None
    return int((value * 100).to_integral_value())


def to_int(text: str, what: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise Invalid(f"{what} must be a whole number") from None


def table(headers: list[str], rows: list[list[str]], label: str) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table aria-label="{label}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>' if rows \
        else "<p>Nothing here yet.</p>"


def link(href: str, text: str) -> str:
    return f'<a href="{href}">{escape(text)}</a>'


# ---- pages ----

def home() -> HTMLResponse:
    with db.transaction() as conn:
        products = catalog.list_products(conn)
        recent = orders.list_orders(conn)[:5]
    low = [p for p in products if p["available"] < 5]
    body = (f"<p>{len(products)} products · {len(recent)} recent orders</p>"
            "<h2>Low stock</h2>" + table(["Product", "Available"],
                                         [[link(f"/products/{p['id']}", p["name"]), str(p["available"])]
                                          for p in low], "Low stock")
            + "<h2>Recent orders</h2>" + table(["Order", "Customer", "Status", "Total"],
                                               [[link(f"/orders/{o['id']}", f"#{o['id']}"),
                                                 escape(o["customer_name"]), escape(o["status"]),
                                                 fmt(o["total_cents"])] for o in recent], "Recent orders"))
    return page("ShopFlow back office", body)


def products_page(error: str = "", status: int = 200) -> HTMLResponse:
    with db.transaction() as conn:
        products = catalog.list_products(conn)
    rows = [[link(f"/products/{p['id']}", p["name"]), escape(p["sku"]), fmt(p["price_cents"]), str(p["available"])]
            for p in products]
    form = """<form method="post" action="/products" aria-label="Add a product"><h2>Add a product</h2>
<label for="sku">SKU</label><input id="sku" name="sku" required>
<label for="name">Name</label><input id="name" name="name" required>
<label for="price">Price ($)</label><input id="price" name="price" required>
<label for="stock">Stock</label><input id="stock" name="stock" value="0">
<p><button type="submit">Add product</button></p></form>"""
    return page("Products", table(["Product", "SKU", "Price", "Available"], rows, "Products") + form, error, status)


def product_page(product_id: int) -> HTMLResponse:
    with db.transaction() as conn:
        try:
            p = catalog.get_product(conn, product_id)
        except NotFound as e:
            return not_found(str(e))
        moves = inventory.movements(conn, product_id)
    body = (f"<p>SKU {escape(p['sku'])} · {fmt(p['price_cents'])}</p>"
            f'<p>On the shelf: <span data-testid="on-hand">{p["on_hand"]}</span> · '
            f'Available to sell: <span data-testid="available">{p["available"]}</span></p>'
            "<h2>Stock movements</h2>"
            + table(["Change", "Reason", "Order", "When"],
                    [[f"{m['change']:+d}", escape(m["reason"]),
                      link(f"/orders/{m['order_id']}", f"#{m['order_id']}") if m["order_id"] else "",
                      escape(m["created_at"])] for m in moves], "Stock movements"))
    return page(p["name"], body)


def customers_page(error: str = "", status: int = 200) -> HTMLResponse:
    with db.transaction() as conn:
        everyone = customers.list_customers(conn)
    rows = [[link(f"/customers/{c['id']}", c["name"]), escape(c["email"]), str(c["points"])] for c in everyone]
    form = """<form method="post" action="/customers" aria-label="Add a customer"><h2>Add a customer</h2>
<label for="cname">Name</label><input id="cname" name="name" required>
<label for="email">E-mail</label><input id="email" name="email" required>
<p><button type="submit">Add customer</button></p></form>"""
    return page("Customers", table(["Customer", "E-mail", "Points"], rows, "Customers") + form, error, status)


def customer_page(customer_id: int) -> HTMLResponse:
    with db.transaction() as conn:
        try:
            c = customers.get_customer(conn, customer_id)
        except NotFound as e:
            return not_found(str(e))
        theirs = orders.list_orders(conn, customer_id)
    body = (f"<p>{escape(c['email'])}</p>"
            f'<p>Loyalty points: <span data-testid="points">{c["points"]}</span></p><h2>Orders</h2>'
            + table(["Order", "Status", "Total"], [[link(f"/orders/{o['id']}", f"#{o['id']}"), escape(o["status"]),
                                                    fmt(o["total_cents"])] for o in theirs], "Orders"))
    return page(c["name"], body)


def orders_page() -> HTMLResponse:
    with db.transaction() as conn:
        everything = orders.list_orders(conn)
    rows = [[link(f"/orders/{o['id']}", f"#{o['id']}"), link(f"/customers/{o['customer_id']}", o["customer_name"]),
             escape(o["status"]), fmt(o["total_cents"]), escape(o["created_at"])] for o in everything]
    return page("Orders", '<p><a href="/orders/new">Place a new order</a></p>'
                + table(["Order", "Customer", "Status", "Total", "Placed"], rows, "Orders"))


def new_order_page(error: str = "", status: int = 200) -> HTMLResponse:
    with db.transaction() as conn:
        everyone = customers.list_customers(conn)
        products = catalog.list_products(conn)
    people = "".join(f'<option value="{c["id"]}">{escape(c["name"])}</option>' for c in everyone)
    goods = '<option value="">(none)</option>' + "".join(
        f'<option value="{p["id"]}">{escape(p["name"])} ({fmt(p["price_cents"])}, {p["available"]} available)'
        f'</option>' for p in products)
    rows = "".join(f"""<label for="product{n}">Product {n}</label><select id="product{n}" name="product{n}">{goods}</select>
<label for="quantity{n}">Quantity {n}</label><input id="quantity{n}" name="quantity{n}" value="1">""" for n in (1, 2, 3))
    form = f"""<form method="post" action="/orders" aria-label="New order">
<label for="customer">Customer</label><select id="customer" name="customer">{people}</select>
{rows}
<label for="coupon">Coupon code</label><input id="coupon" name="coupon">
<p><button type="submit">Place order</button></p></form>"""
    return page("New order", form, error, status)


def order_page(order_id: int, error: str = "", status: int = 200) -> HTMLResponse:
    with db.transaction() as conn:
        try:
            o = orders.get_order(conn, order_id)
        except NotFound as e:
            return not_found(str(e))
        who = customers.get_customer(conn, o["customer_id"])
    lines = table(["Product", "Quantity", "Unit price", "Returned"],
                  [[link(f"/products/{line['product_id']}", line["product_name"]), str(line["quantity"]),
                    fmt(line["unit_price_cents"]), str(line["returned_quantity"])] for line in o["lines"]], "Items")
    refunds = table(["Refund", "Amount", "Reason"], [[f"#{r['id']}", fmt(r["amount_cents"]), escape(r["reason"])]
                                                    for r in o["refunds"]], "Refunds")
    options = "".join(f'<option value="{line["id"]}">{escape(line["product_name"])}</option>' for line in o["lines"])
    customer_link = link(f"/customers/{who['id']}", who["name"])
    body = (f"<p>Customer: {customer_link} · "
            f'Status: <span class="status" data-testid="status">{escape(o["status"])}</span></p>'
            f"<p>Subtotal {fmt(o['subtotal_cents'])} · Discount {fmt(o['discount_cents'])}"
            f"{' (' + escape(o['coupon_code']) + ')' if o['coupon_code'] else ''} · "
            f'Total <span data-testid="total">{fmt(o["total_cents"])}</span> · '
            f'Refunded <span data-testid="refunded">{fmt(o["refunded_cents"])}</span> · '
            f"Points earned {o['points_earned']}</p>"
            + lines + "<h2>Refunds</h2>" + refunds
            + f"""<form method="post" action="/orders/{o['id']}/returns" aria-label="Return items"><h2>Return items</h2>
<label for="line">Item</label><select id="line" name="line">{options}</select>
<label for="rquantity">Quantity</label><input id="rquantity" name="quantity" value="1">
<label for="reason">Reason</label><input id="reason" name="reason">
<p><button type="submit">Return items</button></p></form>""")
    return page(f"Order #{o['id']}", body, error, status)


def coupons_page(error: str = "", status: int = 200) -> HTMLResponse:
    with db.transaction() as conn:
        everything = coupons.list_coupons(conn)
    rows = [[escape(c["code"]), f"{c['value']}%" if c["kind"] == "percent" else fmt(c["value"]),
             fmt(c["min_subtotal_cents"]), escape(c["valid_until"] or "-"),
             f"{c['uses']} / {c['max_uses']}" if c["max_uses"] else str(c["uses"]),
             "yes" if c["active"] else "no"] for c in everything]
    form = """<form method="post" action="/coupons" aria-label="Add a coupon"><h2>Add a coupon</h2>
<label for="code">Code</label><input id="code" name="code" required>
<label for="kind">Kind</label><select id="kind" name="kind"><option value="percent">Percent off</option>
<option value="fixed">Fixed amount off</option></select>
<label for="value">Value (percent, or $ for a fixed amount)</label><input id="value" name="value" required>
<label for="min">Minimum spend ($)</label><input id="min" name="min_spend" value="0">
<label for="until">Valid until (YYYY-MM-DD, optional)</label><input id="until" name="valid_until">
<label for="maxuses">Maximum uses (optional)</label><input id="maxuses" name="max_uses">
<p><button type="submit">Add coupon</button></p></form>"""
    return page("Coupons", table(["Code", "Discount", "Minimum spend", "Valid until", "Uses", "Active"], rows,
                                 "Coupons") + form, error, status)


def install(app: FastAPI) -> None:
    get = lambda path: app.get(path, response_class=HTMLResponse, include_in_schema=False)    # noqa: E731
    post = lambda path: app.post(path, response_class=HTMLResponse, include_in_schema=False)  # noqa: E731

    # the page functions also take an error message for re-showing a form; only the path reaches them from a URL
    get("/")(lambda: home())
    get("/products")(lambda: products_page())
    get("/products/{product_id}")(product_page)
    get("/customers")(lambda: customers_page())
    get("/customers/{customer_id}")(customer_page)
    get("/orders")(lambda: orders_page())
    get("/orders/new")(lambda: new_order_page())

    @get("/orders/{order_id}")
    def show_order(order_id: int):
        return order_page(order_id)

    get("/coupons")(lambda: coupons_page())

    @post("/products")
    async def add_product(request: Request):
        f = await form_data(request)
        try:
            with db.transaction() as conn:
                p = catalog.create_product(conn, f.get("sku", ""), f.get("name", ""), to_cents(f.get("price", "")),
                                           to_int(f.get("stock") or "0", "Stock"))
        except (Invalid, Conflict) as e:
            return products_page(str(e), 400)
        return RedirectResponse(f"/products/{p['id']}", status_code=303)

    @post("/customers")
    async def add_customer(request: Request):
        f = await form_data(request)
        try:
            with db.transaction() as conn:
                c = customers.create_customer(conn, f.get("name", ""), f.get("email", ""))
        except (Invalid, Conflict) as e:
            return customers_page(str(e), 400)
        return RedirectResponse(f"/customers/{c['id']}", status_code=303)

    @post("/orders")
    async def add_order(request: Request):
        f = await form_data(request)
        try:
            items = [{"product_id": to_int(f[f"product{n}"], "Product"),
                      "quantity": to_int(f.get(f"quantity{n}") or "1", "Quantity")}
                     for n in (1, 2, 3) if f.get(f"product{n}")]
            with db.transaction() as conn:
                o = orders.place(conn, to_int(f.get("customer", ""), "Customer"), items, f.get("coupon") or None)
        except (Invalid, Conflict, NotFound) as e:
            return new_order_page(str(e), 400)
        return RedirectResponse(f"/orders/{o['id']}", status_code=303)

    @post("/orders/{order_id}/returns")
    async def add_return(order_id: int, request: Request):
        f = await form_data(request)
        try:
            with db.transaction() as conn:
                returns.return_items(conn, order_id, [{"line_id": to_int(f.get("line", ""), "Item"),
                                                       "quantity": to_int(f.get("quantity") or "1", "Quantity")}],
                                     f.get("reason", ""))
        except (Invalid, Conflict) as e:
            return order_page(order_id, str(e), 400)
        except NotFound as e:
            return not_found(str(e))
        return RedirectResponse(f"/orders/{order_id}", status_code=303)

    @post("/coupons")
    async def add_coupon(request: Request):
        f = await form_data(request)
        try:
            with db.transaction() as conn:
                kind = f.get("kind") or "percent"
                value = to_int(f.get("value", ""), "Value") if kind == "percent" else to_cents(f.get("value", ""))
                coupons.create_coupon(conn, f.get("code", ""), kind, value, to_cents(f.get("min_spend") or "0"),
                                      f.get("valid_until") or None,
                                      to_int(f["max_uses"], "Maximum uses") if f.get("max_uses") else None)
        except (Invalid, Conflict) as e:
            return coupons_page(str(e), 400)
        return RedirectResponse("/coupons", status_code=303)
