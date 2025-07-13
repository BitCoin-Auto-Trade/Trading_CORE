"""
매매 신호(Trading Signal) 관련 API 라우터를 정의하는 모듈입니다.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from app.core.db import get_redis
from app.schemas.core import TradingSignal
import redis

router = APIRouter()


@router.get(
    "/combined/{symbol}",
    response_model=TradingSignal,
    summary="저장된 최종 매매 신호 조회",
    description="스케줄러에 의해 주기적으로 분석 및 저장된 최종 매매 신호를 조회합니다.",
)
def get_stored_trading_signal(
    symbol: str, redis_client: redis.Redis = Depends(get_redis)
):
    """
    Redis에 저장된 최신 매매 신호 분석 결과를 조회합니다.
    """
    redis_key = f"trading_signal:{symbol.upper()}"
    signal_data = redis_client.get(redis_key)

    if not signal_data:
        raise HTTPException(
            status_code=404,
            detail=f"{symbol.upper()}에 대한 매매 신호를 찾을 수 없습니다. 다음 분석 주기까지 기다려주세요.",
        )

    return json.loads(signal_data)
