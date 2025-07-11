from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import redis_client
from app.api import getdata, signal, order

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    try:
        redis_client.ping()
        print("Successfully connected to Redis")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
    yield
    # 종료 시 실행 (필요 시)

app = FastAPI(lifespan=lifespan)

app.include_router(getdata.router, prefix="/data", tags=["Data"])
app.include_router(signal.router, prefix="/signals", tags=["Trading Signals"])
app.include_router(order.router, prefix="/orders", tags=["Orders"])
