import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """The app with its own empty database (no demo data)."""
    monkeypatch.setenv("SHOPFLOW_DB", str(tmp_path / "shop.sqlite3"))
    monkeypatch.setenv("SHOPFLOW_SEED", "0")
    from shopflow.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_product(client):
    def make(sku="LAMP-01", name="Desk lamp", price_cents=2500, on_hand=10):
        r = client.post("/api/products", json={"sku": sku, "name": name, "price_cents": price_cents,
                                               "on_hand": on_hand})
        assert r.status_code == 201, r.text
        return r.json()
    return make


@pytest.fixture
def make_customer(client):
    def make(name="Asha Rao", email="asha@example.com"):
        r = client.post("/api/customers", json={"name": name, "email": email})
        assert r.status_code == 201, r.text
        return r.json()
    return make


@pytest.fixture
def place_order(client):
    def place(customer_id, items, coupon_code=None):
        body = {"customer_id": customer_id, "items": [{"product_id": p, "quantity": q} for p, q in items]}
        if coupon_code is not None:
            body["coupon_code"] = coupon_code
        return client.post("/api/orders", json=body)
    return place
