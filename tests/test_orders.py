def test_order_takes_stock_and_awards_points(client, make_product, make_customer, place_order):
    """Placing an order makes its items unavailable and earns 1 point per dollar paid."""
    lamp = make_product(price_cents=2500, on_hand=10)
    asha = make_customer()
    r = place_order(asha["id"], [(lamp["id"], 3)])
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["total_cents"] == 7500
    assert order["points_earned"] == 75
    assert client.get(f"/api/products/{lamp['id']}").json()["available"] == 7
    assert client.get(f"/api/customers/{asha['id']}").json()["points"] == 75


def test_coupon_takes_a_percentage_off(client, make_product, make_customer, place_order):
    """A percent coupon takes that share of the subtotal off; codes work in any case."""
    lamp = make_product(price_cents=2500)
    asha = make_customer()
    client.post("/api/coupons", json={"code": "SAVE10", "kind": "percent", "value": 10})
    order = place_order(asha["id"], [(lamp["id"], 2)], "save10").json()
    assert order["subtotal_cents"] == 5000
    assert order["discount_cents"] == 500
    assert order["total_cents"] == 4500
    assert order["coupon_code"] == "SAVE10"


def test_unknown_coupon_is_rejected(client, make_product, make_customer, place_order):
    lamp = make_product()
    asha = make_customer()
    assert place_order(asha["id"], [(lamp["id"], 1)], "NOPE").status_code == 400


def test_not_enough_stock_takes_nothing(client, make_product, make_customer, place_order):
    """An order that can't be filled is refused and leaves every product's stock as it was."""
    lamp = make_product(on_hand=2)
    pen = make_product(sku="PEN-1", name="Pen", price_cents=100, on_hand=50)
    asha = make_customer()
    r = place_order(asha["id"], [(pen["id"], 5), (lamp["id"], 3)])
    assert r.status_code == 409
    assert client.get(f"/api/products/{pen['id']}").json()["available"] == 50


def test_same_product_twice_is_one_line(client, make_product, make_customer, place_order):
    lamp = make_product()
    asha = make_customer()
    order = place_order(asha["id"], [(lamp["id"], 1), (lamp["id"], 2)]).json()
    assert len(order["lines"]) == 1
    assert order["lines"][0]["quantity"] == 3
