def test_pages_render(client, make_product, make_customer, place_order):
    lamp = make_product()
    asha = make_customer()
    order = place_order(asha["id"], [(lamp["id"], 1)]).json()
    for path in ("/", "/products", f"/products/{lamp['id']}", "/customers", f"/customers/{asha['id']}", "/orders",
                 "/orders/new", f"/orders/{order['id']}", "/coupons"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "<h1>" in r.text


def test_new_order_form_shows_stock_errors(client, make_product, make_customer):
    lamp = make_product(on_hand=1)
    asha = make_customer()
    r = client.post("/orders", data={"customer": str(asha["id"]), "product1": str(lamp["id"]), "quantity1": "5"})
    assert r.status_code == 400
    assert "in stock" in r.text
