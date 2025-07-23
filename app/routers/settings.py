"""
거래 설정 관련 API 라우터를 정의하는 모듈입니다.
"""

from fastapi import APIRouter, Depends
import redis

from app.dependencies import RedisClient
from app.schemas.core import TradingSettings
from app.utils.logging import get_logger
from app.core.constants import REDIS_KEYS

router = APIRouter()
logger = get_logger(__name__)

SETTINGS_KEY = REDIS_KEYS["TRADING_SETTINGS"]

@router.get("/trading", response_model=TradingSettings)
def get_trading_settings(redis_client: RedisClient):
    """현재 거래 설정을 조회합니다."""
    settings_data = redis_client.hgetall(SETTINGS_KEY)
    if not settings_data:
        logger.info("Redis에 저장된 설정이 없어 기본 설정을 반환합니다.")
        return TradingSettings()
    
    # Redis에서 가져온 값들의 타입을 Pydantic 모델에 맞게 변환합니다.
    typed_settings = TradingSettings.model_validate(settings_data)
    return typed_settings

@router.post("/trading", response_model=TradingSettings)
def update_trading_settings(
    settings: TradingSettings,
    redis_client: RedisClient
):
    """새로운 거래 설정을 업데이트합니다."""
    try:
        # Pydantic 모델을 dict로 변환하여 Redis에 저장합니다.
        settings_dict = settings.model_dump()
        redis_client.hset(SETTINGS_KEY, mapping=settings_dict)
        logger.info(f"거래 설정이 업데이트되었습니다: {settings_dict}")
        return settings
    except Exception as e:
        logger.error(f"거래 설정 업데이트 실패: {e}")
        raise
