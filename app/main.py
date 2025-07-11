from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import redis_client
from app.api import getdata, signal, order
from app.core.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 애플리케이션 시작 시 실행 ---
    # Redis 연결 확인
    try:
        redis_client.ping()
        print("Successfully connected to Redis")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
    
    # 스케줄러 시작
    start_scheduler()
    
    yield
    
    # --- 애플리케이션 종료 시 실행 ---
    stop_scheduler()

app = FastAPI(lifespan=lifespan)

app.include_router(getdata.router, prefix="/data", tags=["Data"])
app.include_router(signal.router, prefix="/signals", tags=["Trading Signals"])
app.include_router(order.router, prefix="/orders", tags=["Orders"])
