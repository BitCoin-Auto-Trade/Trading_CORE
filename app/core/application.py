"""
FastAPI 애플리케이션 팩토리
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.db import redis_client, SessionLocal
from app.middleware import (
    ResponseCacheMiddleware,
    ErrorHandlingMiddleware,
    LoggingMiddleware
)
from app.routers import data, signals, orders, logs, settings as settings_router
from app.core.scheduler import start_scheduler, stop_scheduler
from app.utils.helpers import create_api_response
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


class ApplicationState:
    """애플리케이션 상태 관리"""
    
    def __init__(self):
        self.services = {}
        self.tasks = {}
        self.is_initialized = False
    
    def add_service(self, name: str, service: Any):
        """서비스 추가"""
        self.services[name] = service
        logger.debug(f"서비스 등록: {name}")
    
    def get_service(self, name: str):
        """서비스 조회"""
        return self.services.get(name)
    
    def add_task(self, name: str, task: asyncio.Task):
        """백그라운드 태스크 추가"""
        self.tasks[name] = task
        logger.debug(f"백그라운드 태스크 등록: {name}")
    
    def get_task(self, name: str):
        """태스크 조회"""
        return self.tasks.get(name)


# 전역 애플리케이션 상태
app_state = ApplicationState()


async def initialize_services():
    """서비스 초기화"""
    logger.info("🚀 서비스 초기화 시작")
    
    # DB 세션 생성
    db = SessionLocal()
    
    # 서비스 의존성 생성
    from app.repository.db_repository import DBRepository
    from app.adapters.binance_adapter import BinanceAdapter
    from app.services.signal_service import SignalService
    from app.services.order_service import OrderService
    
    # Repository 생성
    db_repo = DBRepository(db=db)
    
    # Adapter 생성
    binance_adapter = BinanceAdapter(db=db, redis_client=redis_client)
    
    # Service 생성
    signal_service = SignalService(
        db_repository=db_repo,
        binance_adapter=binance_adapter,
        redis_client=redis_client
    )
    
    order_service = OrderService(
        db_repository=db_repo,
        binance_adapter=binance_adapter,
        signal_service=signal_service,
        redis_client=redis_client,
    )
    
    # 상태에 서비스 등록
    app_state.add_service("db", db)
    app_state.add_service("signal_service", signal_service)
    app_state.add_service("order_service", order_service)
    
    logger.info("✅ 서비스 초기화 완료")
    return signal_service, order_service


async def start_background_tasks(signal_service, order_service):
    """백그라운드 태스크 시작"""
    logger.info("🔄 백그라운드 태스크 시작")
    
    # 포지션 모니터링 태스크
    monitoring_task = asyncio.create_task(order_service.monitor_positions())
    app_state.add_task("position_monitoring", monitoring_task)
    logger.info("  ✓ 포지션 모니터링 태스크")
    
    # 스케줄러 시작
    start_scheduler(signal_service=signal_service, order_service=order_service)
    logger.info("  ✓ 신호 분석 스케줄러")


async def cleanup_services():
    """서비스 정리"""
    logger.info("🛑 서비스 정리 시작")
    
    # 백그라운드 태스크 정리
    for name, task in app_state.tasks.items():
        if not task.done():
            logger.info(f"  ⏹️ {name} 태스크 취소 중")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"  ✓ {name} 태스크 취소 완료")
    
    # 스케줄러 정리
    stop_scheduler()
    logger.info("  ✓ 스케줄러 정리 완료")
    
    # DB 세션 정리
    db = app_state.get_service("db")
    if db:
        db.close()
        logger.info("  ✓ DB 세션 정리 완료")
    
    logger.info("✅ 서비스 정리 완료")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # === 시작 ===
    logger.info("🏁 Trading CORE 애플리케이션 시작")
    
    try:
        # Redis 연결 확인
        redis_client.ping()
        logger.info("  ✓ Redis 연결 확인")
        
        # 서비스 초기화
        signal_service, order_service = await initialize_services()
        
        # 백그라운드 태스크 시작
        await start_background_tasks(signal_service, order_service)
        
        app_state.is_initialized = True
        logger.info("🎉 Trading CORE 애플리케이션 초기화 완료")
        
    except Exception as e:
        logger.error(f"❌ 애플리케이션 초기화 실패: {e}")
        raise RuntimeError(f"애플리케이션을 시작할 수 없습니다: {e}")
    
    yield
    
    # === 종료 ===
    logger.info("🏁 Trading CORE 애플리케이션 종료 시작")
    await cleanup_services()
    logger.info("👋 Trading CORE 애플리케이션 종료 완료")


def setup_middleware(app: FastAPI):
    """미들웨어 설정"""
    
    # CORS 미들웨어 (가장 먼저)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 에러 핸들링 미들웨어
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 로깅 미들웨어 (간소화된 로깅, 에러만 응답 로깅)
    app.add_middleware(LoggingMiddleware, log_requests=False, log_responses=True)
    
    # 캐싱 미들웨어 (가장 마지막)
    app.add_middleware(ResponseCacheMiddleware)
    
    logger.info("✓ 미들웨어 설정 완료")


def setup_routes(app: FastAPI):
    """라우터 설정"""
    
    # API 라우터 등록
    app.include_router(data.router, prefix="/api/v1/data", tags=["Data"])
    app.include_router(signals.router, prefix="/api/v1/signals", tags=["Signals"])
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
    app.include_router(logs.router, prefix="/api/v1/logs", tags=["Logs"])
    app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
    
    # 기본 엔드포인트
    @app.get("/")
    async def root():
        """API 루트 엔드포인트"""
        return create_api_response(
            success=True,
            data={
                "name": "Trading CORE API",
                "version": "1.0.0",
                "status": "healthy" if app_state.is_initialized else "initializing"
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
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            db.close()
            
            return create_api_response(
                success=True,
                data={
                    "status": "healthy",
                    "redis": "connected",
                    "database": "connected",
                    "services": "initialized" if app_state.is_initialized else "initializing"
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
    
    logger.info("✓ 라우터 설정 완료")


# 애플리케이션 인스턴스 생성 (모듈 레벨에서 한 번만)
_app_instance = None

def create_application() -> FastAPI:
    """FastAPI 애플리케이션 생성"""
    global _app_instance
    
    # 이미 생성된 인스턴스가 있으면 반환 (중복 생성 방지)
    if _app_instance is not None:
        return _app_instance
    
    # 로깅 설정 (중복 방지)
    setup_logging()
    logger.info("📦 FastAPI 애플리케이션 생성 시작")
    
    # FastAPI 애플리케이션 생성
    app = FastAPI(
        title="Trading CORE API",
        description="암호화폐 자동거래 시스템 API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # 미들웨어 설정
    setup_middleware(app)
    
    # 라우터 설정
    setup_routes(app)
    
    logger.info("🚀 FastAPI 애플리케이션 생성 완료")
    
    # 전역 인스턴스 저장
    _app_instance = app
    return app


# 애플리케이션 인스턴스 생성
app = create_application()
