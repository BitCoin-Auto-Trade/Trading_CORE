import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import redis_client, SessionLocal
from app.routers import data, signals, orders
from app.core.scheduler import start_scheduler, stop_scheduler
from app.services.order_service import OrderService
from app.services.signal_service import SignalService
from app.adapters.binance_adapter import BinanceAdapter
from app.repository.db_repository import DBRepository

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
    logger.info("애플리케이션 시작 프로세스를 개시합니다.")
    
    # Redis 연결 확인
    try:
        redis_client.ping()
        logger.info("Redis에 성공적으로 연결되었습니다.")
    except Exception as e:
        logger.error(f"Redis 연결 실패: {e}")
        # Redis 연결 실패 시, 앱 실행을 중단하거나 재시도 로직 추가 가능
        return

    # 서비스 인스턴스 생성
    # lifespan 동안 단일 DB 세션을 사용하여 서비스 인스턴스 생성
    db = SessionLocal()
    db_repo = DBRepository(db=db)
    binance_adapter = BinanceAdapter(db=db, redis_client=redis_client)
    signal_service = SignalService(db_repository=db_repo, binance_adapter=binance_adapter, redis_client=redis_client)
    order_service = OrderService(
        db_repository=db_repo,
        binance_adapter=binance_adapter,
        signal_service=signal_service,
        redis_client=redis_client,
    )

    # OrderService의 포지션 모니터링을 백그라운드 태스크로 시작
    monitoring_task = asyncio.create_task(order_service.monitor_positions())
    logger.info("OrderService 포지션 모니터링이 백그라운드에서 시작되었습니다.")

    # 스케줄러 시작 (진입 신호 분석용)
    start_scheduler()

    yield

    # --- 애플리케이션 종료 시 실행 ---
    logger.info("애플리케이션 종료 프로세스를 시작합니다.")
    
    # 백그라운드 태스크 종료
    monitoring_task.cancel()
    try:
        await monitoring_task
    except asyncio.CancelledError:
        logger.info("포지션 모니터링 태스크가 성공적으로 취소되었습니다.")

    # 스케줄러 중지
    stop_scheduler()
    
    # DB 세션 종료
    db.close()
    logger.info("DB 세션이 종료되었습니다.")


app = FastAPI(lifespan=lifespan)

app.include_router(data.router, prefix="/data", tags=["Data"])
app.include_router(signals.router, prefix="/signals", tags=["Trading Signals"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
