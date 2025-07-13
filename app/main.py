import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import redis_client
from app.routers import data, signals, orders
from app.core.scheduler import start_scheduler, stop_scheduler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 애플리케이션 시작 시 실행 ---
    # Redis 연결 확인
    try:
        redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")

    # 스케줄러 시작
    start_scheduler()

    yield

    # --- 애플리케이션 종료 시 실행 ---
    stop_scheduler()


app = FastAPI(lifespan=lifespan)

app.include_router(data.router, prefix="/data", tags=["Data"])
app.include_router(signals.router, prefix="/signals", tags=["Trading Signals"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
