"""The ShopFlow app: `uvicorn shopflow.main:app`. The JSON API is under /api (its spec at /openapi.json and in
openapi.json at the repo root); the back-office pages are everything else."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from shopflow import api, db, seed, web


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    seed.seed_if_empty()
    yield


app = FastAPI(title="ShopFlow", version="1.0.0", lifespan=lifespan,
              description="A small shop back office: products and stock, customers and loyalty points, coupons, "
                          "orders and returns.")
api.install(app)
web.install(app)
