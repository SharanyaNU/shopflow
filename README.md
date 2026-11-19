# ShopFlow

A small shop back office: products and stock, customers and their loyalty points, coupons, orders and returns.
FastAPI with a JSON API under `/api` and plain HTML pages for staff.

## Run it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows; on macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m uvicorn shopflow.main:app --port 8000
```

Open http://127.0.0.1:8000. A new database (`instance/shopflow.sqlite3`) is created and filled with demo data on
first start; set `SHOPFLOW_DB` to use another file and `SHOPFLOW_SEED=0` to start empty.

Tests: `python -m pytest`. API spec: `openapi.json` (regenerate with `python scripts/export_openapi.py`), also served
at `/openapi.json`.

## Business rules

**Products and stock**
- SKUs are unique and stored in upper case. Prices and stock can't be negative.
- Every change to stock is recorded as a stock movement (initial stock, shipped, return).
- Catalogue search matches the product's name or SKU, ignoring case. The catalogue page shows 5 products per page.
- Best sellers: units in orders that weren't cancelled, minus units returned. The home page shows the top 3.
- Stock has two numbers: on the shelf (`on_hand`) and reserved for orders that haven't shipped (`reserved`).
  Available to sell = on the shelf − reserved.
- An order can't reserve more items than are available: it is refused with 409 and nothing is reserved.

**Customers and loyalty**
- E-mail addresses are unique, compared without case.
- Customers earn 1 loyalty point per whole dollar they pay for an order (after the discount).
- When money is refunded, the points that money earned are taken back. A balance never goes below 0.

**Coupons**
- A coupon takes either a percentage (1–100) off the order's subtotal, rounded down to a cent, or a fixed amount.
- A fixed coupon never takes more than the subtotal: an order's total is never below $0.00.
- Minimum spend: the coupon needs a subtotal of **at least** `min_subtotal_cents`.
- `valid_until` is the last day the coupon can be used (inclusive).
- `max_uses`: the coupon can be used by that many orders in total, then it is refused.
- Codes are kept as typed but are case-insensitive: `Spring15`, `SPRING15` and `spring15` are the same coupon.
- Unknown, inactive, expired or used-up codes, and orders below the minimum spend, are refused with 400.

**Orders**
- An order has at least one item, each with a quantity of at least 1. The same product twice is one line.
- An order goes **placed → shipped**. Placing it reserves the items, charges subtotal − discount and awards the
  loyalty points. Shipping takes the reserved items off the shelf.
- An order can be **cancelled until it ships**: the reservation is released, the customer gets back what they paid
  and the points the order earned are taken back. A shipped order can't be cancelled (409).

**Returns**
- Items of an order can be returned, never more of a line than was bought (counting earlier returns).
- Returned items go back into stock.
- The refund is what the customer paid for those items: the coupon discount is shared across the order's items in
  proportion to their price. An order never refunds more in total than was paid for it.
- A cancelled order can't be returned.

## Pages

| Page | What it shows |
|---|---|
| `/` | low-stock products and recent orders |
| `/products`, `/products/{id}` | the catalogue, a form to add a product; one product's stock and its movements |
| `/customers`, `/customers/{id}` | customers, a form to add one; one customer's points and orders |
| `/orders`, `/orders/new`, `/orders/{id}` | orders; the form to place one; one order with its items, refunds and a return form |
| `/coupons` | coupons and a form to add one |

## Layout

```
shopflow/main.py       the app (FastAPI), its start-up (database + demo data)
shopflow/api.py        the JSON API: request/response shapes, errors -> status codes
shopflow/web.py        the HTML pages and their forms
shopflow/catalog.py    products          shopflow/inventory.py  stock and stock movements
shopflow/customers.py  customers         shopflow/loyalty.py    loyalty points
shopflow/coupons.py    coupons           shopflow/pricing.py    an order's subtotal, discount and total
shopflow/orders.py     placing orders    shopflow/returns.py    returns and refunds
shopflow/db.py         SQLite schema     shopflow/seed.py       demo data
tests/                 pytest tests (a temporary database per test)
```
