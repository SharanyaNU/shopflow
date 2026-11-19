def test_create_product_uppercases_sku(client):
    """SKUs are stored in upper case, whatever case they are sent in."""
    r = client.post("/api/products", json={"sku": "mug-01", "name": "Coffee mug", "price_cents": 1200, "on_hand": 3})
    assert r.status_code == 201
    assert r.json()["sku"] == "MUG-01"
    assert r.json()["available"] == 3


def test_duplicate_sku_is_a_conflict(client, make_product):
    """Two products can't share a SKU, even when it differs only in case."""
    make_product(sku="LAMP-01")
    r = client.post("/api/products", json={"sku": "lamp-01", "name": "Other lamp", "price_cents": 100})
    assert r.status_code == 409


def test_negative_price_is_rejected(client):
    r = client.post("/api/products", json={"sku": "X-1", "name": "X", "price_cents": -1})
    assert r.status_code == 422


def test_unknown_product_is_404(client):
    assert client.get("/api/products/999").status_code == 404


def test_customer_emails_are_unique_without_case(client, make_customer):
    """A second customer with the same e-mail in another case is refused."""
    make_customer(email="asha@example.com")
    r = client.post("/api/customers", json={"name": "Asha again", "email": "ASHA@example.com"})
    assert r.status_code == 409
