"""
개선된 의존성 주입 시스템
"""
from functools import lru_cache
from typing import Annotated, Generator, List
from fastapi import Depends
from sqlalchemy.orm import Session
import redis

from app.core.db import get_db, get_redis
from app.repository.db_repository import DBRepository
from app.repository.redis_repository import RedisRepository
from app.adapters.binance_adapter import BinanceAdapter
from app.services.signal_service import SignalService
from app.services.order_service import OrderService
from app.utils.logging import get_logger

logger = get_logger(__name__)


# === 기본 의존성 ===
DbSession = Annotated[Session, Depends(get_db)]
RedisClient = Annotated[redis.Redis, Depends(get_redis)]


# === Repository 의존성 ===
def get_db_repository(db: DbSession) -> DBRepository:
    """DB Repository 인스턴스를 반환합니다."""
    return DBRepository(db=db)


def get_redis_repository(redis_client: RedisClient) -> RedisRepository:
    """Redis Repository 인스턴스를 반환합니다."""
    return RedisRepository(redis_client=redis_client)


DbRepository = Annotated[DBRepository, Depends(get_db_repository)]
DbRepositoryDep = DbRepository  # 별칭 추가
RedisRepo = Annotated[RedisRepository, Depends(get_redis_repository)]


# === Adapter 의존성 ===
@lru_cache()
def get_binance_adapter_factory():
    """Binance Adapter Factory를 반환합니다."""
    def create_adapter(db: DbSession, redis_client: RedisClient, testnet: bool = False) -> BinanceAdapter:
        return BinanceAdapter(db=db, redis_client=redis_client, testnet=testnet)
    return create_adapter


def get_binance_adapter(
    db: DbSession,
    redis_client: RedisClient,
    testnet: bool = False
) -> BinanceAdapter:
    """Binance Adapter 인스턴스를 반환합니다."""
    factory = get_binance_adapter_factory()
    return factory(db=db, redis_client=redis_client, testnet=testnet)


BinanceAdapterDep = Annotated[BinanceAdapter, Depends(get_binance_adapter)]


# === Service 의존성 ===
def get_signal_service(
    db_repo: DbRepository,
    binance_adapter: BinanceAdapterDep,
    redis_client: RedisClient,
) -> SignalService:
    """Signal Service 인스턴스를 반환합니다."""
    return SignalService(
        db_repository=db_repo,
        binance_adapter=binance_adapter,
        redis_client=redis_client
    )


def get_order_service(
    db_repo: DbRepository,
    binance_adapter: BinanceAdapterDep,
    signal_service: Annotated[SignalService, Depends(get_signal_service)],
    redis_client: RedisClient,
) -> OrderService:
    """Order Service 인스턴스를 반환합니다."""
    return OrderService(
        db_repository=db_repo,
        binance_adapter=binance_adapter,
        signal_service=signal_service,
        redis_client=redis_client,
    )


SignalServiceDep = Annotated[SignalService, Depends(get_signal_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


# === 유틸리티 의존성 ===
class DependencyManager:
    """의존성 관리자"""
    
    @staticmethod
    def get_all_position_symbols() -> List[str]:
        """모든 포지션 심볼 목록을 반환하는 유틸리티 메서드"""
        try:
            with ServiceContext() as ctx:
                redis_client = ctx.get_redis_client()
                from app.core.constants import REDIS_KEYS
                pattern = f"{REDIS_KEYS['POSITION_PREFIX']}*"
                keys = redis_client.keys(pattern)
                symbols = []
                for key in keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                    # position:SYMBOL 형태에서 SYMBOL 추출
                    parts = key_str.split(':')
                    if len(parts) >= 2:
                        symbols.append(parts[1])
                return symbols
        except Exception as e:
            logger.error(f"포지션 심볼 목록 조회 중 오류: {e}")
            return []
    
    @staticmethod
    def validate_dependencies():
        """의존성 유효성 검증"""
        try:
            # DB 연결 테스트
            from app.core.db import SessionLocal
            with SessionLocal() as db:
                db.execute("SELECT 1")
            
            # Redis 연결 테스트  
            from app.core.db import redis_client
            redis_client.ping()
            
            logger.info("모든 의존성 검증 완료")
            return True
        except Exception as e:
            logger.error(f"의존성 검증 실패: {e}")
            return False

    @staticmethod
    def get_health_dependencies() -> dict:
        """헬스체크 의존성"""
        return {
            "database": get_db,
            "redis": get_redis,
        }
    
    @staticmethod
    def clear_caches():
        """모든 캐시 초기화"""
        logger.info("의존성 캐시 초기화 중...")
        get_binance_adapter_factory.cache_clear()
        logger.info("의존성 캐시 초기화 완료")


# === 컨텍스트 매니저 ===
class ServiceContext:
    """서비스 컨텍스트 관리자"""
    
    def __init__(self):
        self._db: Session = None
        self._redis: redis.Redis = None
        self._repositories = {}
        self._services = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._db:
            self._db.close()
    
    def get_db_session(self) -> Session:
        """DB 세션 반환"""
        if not self._db:
            from app.core.db import SessionLocal
            self._db = SessionLocal()
        return self._db
    
    def get_redis_client(self) -> redis.Redis:
        """Redis 클라이언트 반환"""
        if not self._redis:
            from app.core.db import redis_client
            self._redis = redis_client
        return self._redis


# === 전역 의존성 관리자 인스턴스 ===
dependency_manager = DependencyManager()
