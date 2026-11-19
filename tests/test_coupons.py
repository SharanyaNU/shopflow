def test_fixed_coupon_takes_an_amount_off(client, make_product, make_customer, place_order):
    """A fixed coupon takes its amount off an order that meets its minimum spend."""
    chair = make_product(sku="CHAIR-01", name="Office chair", price_cents=14900)
    asha = make_customer()
    r = client.post("/api/coupons", json={"code": "TENOFF", "kind": "fixed", "value": 1000,
                                          "min_subtotal_cents": 5000})
    assert r.status_code == 201, r.text
    order = place_order(asha["id"], [(chair["id"], 1)], "TENOFF").json()
    assert order["discount_cents"] == 1000
    assert order["total_cents"] == 13900


def test_coupon_lists_its_uses(client, make_product, make_customer, place_order):
    lamp = make_product()
    asha = make_customer()
    client.post("/api/coupons", json={"code": "SAVE5", "kind": "percent", "value": 5, "max_uses": 10})
    place_order(asha["id"], [(lamp["id"], 1)], "SAVE5")
    coupon = next(c for c in client.get("/api/coupons").json() if c["code"] == "SAVE5")
    assert coupon["uses"] == 1
