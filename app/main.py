from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.core.db import engine, redis_client, get_db, get_redis
from app.models import Base
# 생성한 모델들을 import 합니다.
from app.models.kline import Kline_1m
from app.models.funding_rate import FundingRate
from app.models.open_interest import OpenInterest

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

@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading Core API"}
