"""The JSON API under /api. Business rules live in the modules it calls; this file only checks shapes and maps
errors to status codes (404 not found, 409 conflict, 400 invalid request, 422 malformed body)."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from shopflow import catalog, coupons, customers, db, orders, returns
from shopflow.errors import Conflict, Invalid, NotFound


class Error(BaseModel):
    detail: str


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    price_cents: int = Field(ge=0)
    on_hand: int = Field(0, ge=0)


class Product(BaseModel):
    id: int
    sku: str
    name: str
    price_cents: int
    on_hand: int
    available: int


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=200)


class Customer(BaseModel):
    id: int
    name: str
    email: str
    points: int


class CouponIn(BaseModel):
    code: str = Field(min_length=3, max_length=30)
    kind: Literal["percent", "fixed"] = "percent"
    value: int = Field(ge=1, description="percent: 1-100 percent off; fixed: cents off")
    min_subtotal_cents: int = Field(0, ge=0, description="the coupon needs a subtotal of at least this")
    valid_until: date | None = Field(None, description="last day the coupon can be used (inclusive)")
    max_uses: int | None = Field(None, ge=1, description="how many orders can use it in total")


class Coupon(BaseModel):
    code: str
    kind: str
    value: int
    min_subtotal_cents: int
    valid_until: str | None
    max_uses: int | None
    uses: int
    active: bool


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class OrderIn(BaseModel):
    customer_id: int
    items: list[OrderItemIn] = Field(min_length=1)
    coupon_code: str | None = None


class OrderLine(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price_cents: int
    returned_quantity: int


class Refund(BaseModel):
    id: int
    amount_cents: int
    reason: str
    created_at: str


class Order(BaseModel):
    id: int
    customer_id: int
    status: str
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    coupon_code: str | None
    points_earned: int
    created_at: str
    lines: list[OrderLine]
    refunds: list[Refund]
    refunded_cents: int


class OrderSummary(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    status: str
    total_cents: int
    created_at: str


class ReturnItemIn(BaseModel):
    line_id: int
    quantity: int = Field(ge=1)


class ReturnIn(BaseModel):
    items: list[ReturnItemIn] = Field(min_length=1)
    reason: str = Field("", max_length=500)


class ReturnOut(BaseModel):
    refund_id: int
    order_id: int
    amount_cents: int


NOT_FOUND = {404: {"model": Error, "description": "Not found"}}
CONFLICT = {409: {"model": Error, "description": "Not allowed in the current state"}}
INVALID = {400: {"model": Error, "description": "Invalid request"}}

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@router.get("/products", response_model=list[Product], tags=["products"])
def list_products():
    with db.transaction() as conn:
        return catalog.list_products(conn)


@router.post("/products", response_model=Product, status_code=201, tags=["products"], responses={**CONFLICT, **INVALID})
def create_product(body: ProductIn):
    with db.transaction() as conn:
        return catalog.create_product(conn, body.sku, body.name, body.price_cents, body.on_hand)


@router.get("/products/{product_id}", response_model=Product, tags=["products"], responses=NOT_FOUND)
def get_product(product_id: int):
    with db.transaction() as conn:
        return catalog.get_product(conn, product_id)


@router.get("/customers", response_model=list[Customer], tags=["customers"])
def list_customers():
    with db.transaction() as conn:
        return customers.list_customers(conn)


@router.post("/customers", response_model=Customer, status_code=201, tags=["customers"],
             responses={**CONFLICT, **INVALID})
def create_customer(body: CustomerIn):
    with db.transaction() as conn:
        return customers.create_customer(conn, body.name, body.email)


@router.get("/customers/{customer_id}", response_model=Customer, tags=["customers"], responses=NOT_FOUND)
def get_customer(customer_id: int):
    with db.transaction() as conn:
        return customers.get_customer(conn, customer_id)


@router.get("/coupons", response_model=list[Coupon], tags=["coupons"])
def list_coupons():
    with db.transaction() as conn:
        return coupons.list_coupons(conn)


@router.post("/coupons", response_model=Coupon, status_code=201, tags=["coupons"], responses={**CONFLICT, **INVALID})
def create_coupon(body: CouponIn):
    with db.transaction() as conn:
        return coupons.create_coupon(conn, body.code, body.kind, body.value, body.min_subtotal_cents,
                                     body.valid_until.isoformat() if body.valid_until else None, body.max_uses)


@router.get("/orders", response_model=list[OrderSummary], tags=["orders"])
def list_orders(customer_id: int | None = None):
    with db.transaction() as conn:
        return orders.list_orders(conn, customer_id)


@router.post("/orders", response_model=Order, status_code=201, tags=["orders"],
             responses={**NOT_FOUND, **CONFLICT, **INVALID})
def place_order(body: OrderIn):
    """Takes the items from stock, applies the coupon and awards loyalty points. 409 when there isn't enough stock."""
    with db.transaction() as conn:
        return orders.place(conn, body.customer_id, [i.model_dump() for i in body.items], body.coupon_code)


@router.get("/orders/{order_id}", response_model=Order, tags=["orders"], responses=NOT_FOUND)
def get_order(order_id: int):
    with db.transaction() as conn:
        return orders.get_order(conn, order_id)


@router.post("/orders/{order_id}/returns", response_model=ReturnOut, status_code=201, tags=["returns"],
             responses={**NOT_FOUND, **CONFLICT, **INVALID})
def return_items(order_id: int, body: ReturnIn):
    """Puts the items back in stock, refunds what was paid for them and takes back the points that money earned."""
    with db.transaction() as conn:
        return returns.return_items(conn, order_id, [i.model_dump() for i in body.items], body.reason)


def install(app: FastAPI) -> None:
    app.include_router(router)

    @app.exception_handler(NotFound)
    async def not_found(_request: Request, exc: NotFound):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(Conflict)
    async def conflict(_request: Request, exc: Conflict):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(Invalid)
    async def invalid(_request: Request, exc: Invalid):
        return JSONResponse({"detail": str(exc)}, status_code=400)
