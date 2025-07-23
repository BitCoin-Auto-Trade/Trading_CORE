import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.db import redis_client, SessionLocal
from app.routers import data, signals, orders, logs, settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.exceptions import TradingCoreException
from app.utils.helpers import create_api_response
from app.utils.logging import get_logger, setup_logging

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

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
        raise RuntimeError("Redis 연결에 실패했습니다. 애플리케이션을 시작할 수 없습니다.")

    # 서비스 인스턴스 생성 (lifespan에서만 사용)
    from app.services.order_service import OrderService
    from app.services.signal_service import SignalService
    from app.adapters.binance_adapter import BinanceAdapter
    from app.repository.db_repository import DBRepository
    
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
    start_scheduler(signal_service=signal_service, order_service=order_service)

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


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Trading CORE API",
    description="암호화폐 자동거래 시스템 API",
    version="1.0.0",
    lifespan=lifespan
)

# 전역 예외 처리
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """모든 예외를 처리하는 전역 핸들러"""
    status_code = 500
    error_code = "INTERNAL_SERVER_ERROR"
    message = f"서버 내부 오류가 발생했습니다: {exc}"

    if isinstance(exc, TradingCoreException):
        status_code = 400
        error_code = exc.__class__.__name__
        message = str(exc)
    
    logger.error(f"Request URL: {request.url} | Error: {message}", exc_info=True)
    
    return JSONResponse(
        status_code=status_code,
        content=create_api_response(
            success=False,
            message=message,
            error_code=error_code
        )
    )

# API 라우터 등록 (v1 API만 사용)
app.include_router(data.router, prefix="/api/v1/data", tags=["Data"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["Signals"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["Logs"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])

# 루트 엔드포인트
@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return create_api_response(
        success=True,
        data={
            "name": "Trading CORE API",
            "version": "1.0.0",
            "status": "healthy"
        },
        message="Trading CORE API가 정상적으로 작동 중입니다."
    )

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """시스템 헬스체크"""
    try:
        # Redis 연결 확인
        redis_client.ping()
        
        # DB 연결 확인
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return create_api_response(
            success=True,
            data={
                "status": "healthy",
                "redis": "connected",
                "database": "connected"
            },
            message="모든 서비스가 정상적으로 작동 중입니다."
        )
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return create_api_response(
            success=False,
            data={"status": "unhealthy"},
            message=f"서비스 상태 확인 실패: {str(e)}"
        )
