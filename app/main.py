from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    # Base.metadata.create_all(bind=engine) # 테이블이 이미 존재하므로 주석 처리하거나 유지할 수 있습니다.
    try:
        redis_client.ping()
        print("Successfully connected to Redis")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
    yield
    # 종료 시 실행 (필요 시)

app = FastAPI(lifespan=lifespan)

from app.api import signal, order
app.include_router(signal.router, prefix="/signals", tags=["signals"])
app.include_router(order.router, prefix="/orders", tags=["orders"])
