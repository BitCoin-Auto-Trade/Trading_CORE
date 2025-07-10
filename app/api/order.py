from fastapi import APIRouter, Depends
import redis

from app.core.db import get_redis
from app.services.order import OrderService
from app.schemas.order import Kline1mData, OrderBookDepth, TradeData

router = APIRouter()

# --- Dependency Injection --- 
def get_order_service(redis_client: redis.Redis = Depends(get_redis)) -> OrderService:
    return OrderService(redis_client=redis_client)

@router.get("/kline-1m/{symbol}", response_model=Kline1mData | None)
def get_kline_1m(symbol: str, service: OrderService = Depends(get_order_service)):
    """
    특정 심볼의 최신 1분봉 캔들 데이터를 조회합니다.
    """
    return service.get_kline_1m(symbol.upper())

@router.get("/depth/{symbol}", response_model=OrderBookDepth | None)
def get_order_book(symbol: str, service: OrderService = Depends(get_order_service)):
    """
    특정 심볼의 실시간 오더북(호가창) 데이터를 조회합니다.
    """
    return service.get_order_book(symbol.upper())

@router.get("/trades/{symbol}", response_model=list[TradeData])
def get_recent_trades(symbol: str, limit: int = 100, service: OrderService = Depends(get_order_service)):
    """
    특정 심볼의 최근 체결 내역을 조회합니다.
    """
    return service.get_trades(symbol.upper(), limit)
