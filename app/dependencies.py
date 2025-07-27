"""
의존성 주입을 위한 공통 모듈 - 새로운 구조로 리팩토링됨
"""
# 기존 호환성을 위한 임포트
from app.core.dependencies import (
    DbSession,
    RedisClient,
    DbRepository,
    RedisRepo,
    BinanceAdapterDep,
    SignalServiceDep,
    OrderServiceDep,
    dependency_manager,
    ServiceContext
)

# 기존 함수들의 호환성 유지
def get_db_repository(db: DbSession) -> DbRepository:
    """기존 호환성을 위한 래퍼"""
    from app.core.dependencies import get_db_repository as new_get_db_repository
    return new_get_db_repository(db)


def get_redis_repository(redis_client: RedisClient) -> RedisRepo:
    """기존 호환성을 위한 래퍼"""
    from app.core.dependencies import get_redis_repository as new_get_redis_repository
    return new_get_redis_repository(redis_client)


def get_binance_adapter(db: DbSession, redis_client: RedisClient, testnet: bool = False) -> BinanceAdapterDep:
    """기존 호환성을 위한 래퍼"""
    from app.core.dependencies import get_binance_adapter as new_get_binance_adapter
    return new_get_binance_adapter(db=db, redis_client=redis_client, testnet=testnet)


def get_signal_service(
    db_repo: DbRepository,
    binance_adapter: BinanceAdapterDep,
    redis_client: RedisClient,
) -> SignalServiceDep:
    """기존 호환성을 위한 래퍼"""
    from app.core.dependencies import get_signal_service as new_get_signal_service
    return new_get_signal_service(
        db_repo=db_repo,
        binance_adapter=binance_adapter,
        redis_client=redis_client
    )


def get_order_service(
    db_repo: DbRepository,
    binance_adapter: BinanceAdapterDep,
    signal_service: SignalServiceDep,
    redis_client: RedisClient,
) -> OrderServiceDep:
    """기존 호환성을 위한 래퍼"""
    from app.core.dependencies import get_order_service as new_get_order_service
    return new_get_order_service(
        db_repo=db_repo,
        binance_adapter=binance_adapter,
        signal_service=signal_service,
        redis_client=redis_client
    )


def get_health_check_dependencies() -> dict:
    """기존 호환성을 위한 래퍼"""
    return dependency_manager.get_health_dependencies()


def clear_dependency_cache():
    """기존 호환성을 위한 래퍼"""
    dependency_manager.clear_caches()
