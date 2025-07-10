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

@app.get("/test-data")
def get_test_data(db: Session = Depends(get_db), redis = Depends(get_redis)):
    # --- 1. Redis 데이터 가져오기 ---
    # 키 이름은 실제 사용하는 키로 변경해야 할 수 있습니다.
    kline_data_raw = redis.get("binance:kline:btcusdt:1m")
    kline_data = json.loads(kline_data_raw) if kline_data_raw else None

    depth_data_raw = redis.get("binance:depth:btcusdt")
    depth_data = json.loads(depth_data_raw) if depth_data_raw else None

    trades_data_raw = redis.lrange("binance:trades:btcusdt", 0, 4) # 최근 5개만 가져오기
    trades_data = [json.loads(trade) for trade in trades_data_raw]

    # --- 2. PostgreSQL 데이터 가져오기 ---
    # 최신 데이터 1개를 기준으로 가져옵니다.
    latest_kline = db.query(Kline_1m).order_by(Kline_1m.timestamp.desc()).first()
    latest_funding_rate = db.query(FundingRate).order_by(FundingRate.timestamp.desc()).first()
    latest_open_interest = db.query(OpenInterest).order_by(OpenInterest.timestamp.desc()).first()

    return {
        "redis_data": {
            "kline_1m": kline_data,
            "order_book_depth": depth_data,
            "recent_trades": trades_data
        },
        "postgresql_data": {
            "latest_kline_with_indicators": latest_kline,
            "latest_funding_rate": latest_funding_rate,
            "latest_open_interest": latest_open_interest
        }
    }

# API 라우터 포함 (아직 라우터가 없으므로 주석 처리)
# from app.api import account, order, signal
# app.include_router(account.router, prefix="/accounts", tags=["accounts"])
# app.include_router(order.router, prefix="/orders", tags=["orders"])
# app.include_router(signal.router, prefix="/signals", tags=["signals"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading Core API"}
