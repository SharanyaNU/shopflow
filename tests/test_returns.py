def _shipped_order(client, place_order, customer_id, items, coupon_code=None):
    order = place_order(customer_id, items, coupon_code).json()
    assert client.post(f"/api/orders/{order['id']}/ship").status_code == 200
    return order


def test_return_refunds_the_discounted_price_and_restocks(client, make_product, make_customer, place_order):
    """A returned item refunds what was paid for it (after the coupon) and goes back into stock."""
    lamp = make_product(price_cents=2000, on_hand=5)
    asha = make_customer()
    client.post("/api/coupons", json={"code": "TWENTY", "kind": "percent", "value": 20})
    order = _shipped_order(client, place_order, asha["id"], [(lamp["id"], 2)], "TWENTY")
    r = client.post(f"/api/orders/{order['id']}/returns",
                    json={"items": [{"line_id": order["lines"][0]["id"], "quantity": 1}]})
    assert r.status_code == 201, r.text
    assert r.json()["amount_cents"] == 1600
    assert client.get(f"/api/products/{lamp['id']}").json()["available"] == 4


def test_cannot_return_more_than_bought(client, make_product, make_customer, place_order):
    """A line can't be returned more often than it was bought, counting earlier returns."""
    lamp = make_product()
    asha = make_customer()
    order = _shipped_order(client, place_order, asha["id"], [(lamp["id"], 2)])
    line = order["lines"][0]["id"]
    assert client.post(f"/api/orders/{order['id']}/returns",
                       json={"items": [{"line_id": line, "quantity": 2}]}).status_code == 201
    assert client.post(f"/api/orders/{order['id']}/returns",
                       json={"items": [{"line_id": line, "quantity": 1}]}).status_code == 409


def test_return_takes_back_points(client, make_product, make_customer, place_order):
    lamp = make_product(price_cents=2500)
    asha = make_customer()
    order = _shipped_order(client, place_order, asha["id"], [(lamp["id"], 2)])
    client.post(f"/api/orders/{order['id']}/returns",
                json={"items": [{"line_id": order["lines"][0]["id"], "quantity": 1}]})
    assert client.get(f"/api/customers/{asha['id']}").json()["points"] == 25
