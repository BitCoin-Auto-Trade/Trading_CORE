"""
의존성 주입을 위한 공통 모듈입니다.
"""
from functools import lru_cache
from typing import Annotated
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


# 기본 의존성
DbSession = Annotated[Session, Depends(get_db)]
RedisClient = Annotated[redis.Redis, Depends(get_redis)]


# Repository 의존성
@lru_cache()
def get_db_repository(db: DbSession) -> DBRepository:
    """DB Repository 인스턴스를 반환합니다."""
    logger.debug("DB Repository 인스턴스 생성")
    return DBRepository(db=db)


@lru_cache()
def get_redis_repository(redis_client: RedisClient) -> RedisRepository:
    """Redis Repository 인스턴스를 반환합니다."""
    logger.debug("Redis Repository 인스턴스 생성")
    return RedisRepository(redis_client=redis_client)


DbRepository = Annotated[DBRepository, Depends(get_db_repository)]
RedisRepo = Annotated[RedisRepository, Depends(get_redis_repository)]


# Adapter 의존성
@lru_cache()
def get_binance_adapter(
    db: DbSession,
    redis_client: RedisClient,
    testnet: bool = False
) -> BinanceAdapter:
    """Binance Adapter 인스턴스를 반환합니다."""
    logger.debug(f"Binance Adapter 인스턴스 생성 (testnet={testnet})")
    return BinanceAdapter(db=db, redis_client=redis_client, testnet=testnet)


BinanceAdapterDep = Annotated[BinanceAdapter, Depends(get_binance_adapter)]


# Service 의존성
@lru_cache()
def get_signal_service(
    db_repo: DbRepository,
    binance_adapter: BinanceAdapterDep,
    redis_client: RedisClient,
) -> SignalService:
    """Signal Service 인스턴스를 반환합니다."""
    logger.debug("Signal Service 인스턴스 생성")
    return SignalService(
        db_repository=db_repo,
        binance_adapter=binance_adapter,
        redis_client=redis_client
    )


@lru_cache()
def get_order_service(
    db_repo: DbRepository,
    binance_adapter: BinanceAdapterDep,
    signal_service: Annotated[SignalService, Depends(get_signal_service)],
    redis_client: RedisClient,
) -> OrderService:
    """Order Service 인스턴스를 반환합니다."""
    logger.debug("Order Service 인스턴스 생성")
    return OrderService(
        db_repository=db_repo,
        binance_adapter=binance_adapter,
        signal_service=signal_service,
        redis_client=redis_client,
    )


SignalServiceDep = Annotated[SignalService, Depends(get_signal_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


# 헬스체크 의존성
def get_health_check_dependencies() -> dict:
    """헬스체크에 필요한 의존성들을 반환합니다."""
    return {
        "database": get_db,
        "redis": get_redis,
    }


# 캐시 초기화 함수
def clear_dependency_cache():
    """의존성 캐시를 초기화합니다."""
    logger.info("의존성 캐시 초기화")
    get_db_repository.cache_clear()
    get_redis_repository.cache_clear()
    get_binance_adapter.cache_clear()
    get_signal_service.cache_clear()
    get_order_service.cache_clear()
