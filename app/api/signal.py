"""
매매 신호 관련 API 라우터를 정의하는 모듈입니다.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from app.core.db import get_redis
from app.schemas.signal_schema import TradingSignal
import redis

router = APIRouter()

@router.get("/combined/{symbol}", response_model=TradingSignal, summary="저장된 종합 매매 신호 조회")
def get_stored_trading_signal(symbol: str, redis_client: redis.Redis = Depends(get_redis)):
    """
    스케줄러가 1분마다 분석하여 Redis에 저장한 최신 매매 신호 결과를 조회합니다.

    - **symbol**: `BTCUSDT`, `ETHUSDT`
    - **응답**: 저장된 신호가 없을 경우 404 에러를 반환합니다.
    """
    redis_key = f"trading_signal:{symbol.upper()}"
    signal_data = redis_client.get(redis_key)
    
    if not signal_data:
        raise HTTPException(status_code=404, detail=f"Trading signal for {symbol.upper()} not found. Please wait for the next analysis cycle.")
    
    return json.loads(signal_data)
