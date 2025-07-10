from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis

from app.core.db import get_db, get_redis
from app.services.order import OrderService
from app.services.signal import SignalService
from app.schemas.order import Kline1mData, OrderBookDepth, TradeData
from app.schemas.signal import KlineBase, FundingRateBase, OpenInterestBase

router = APIRouter()

# --- Dependency Injection --- 
def get_order_service(redis_client: redis.Redis = Depends(get_redis)) -> OrderService:
    return OrderService(redis_client=redis_client)

def get_signal_service(db: Session = Depends(get_db)) -> SignalService:
    return SignalService(db=db)


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

@router.get("/klines/{symbol}", response_model=list[KlineBase])
def get_klines_data(symbol: str, limit: int = 100, service: SignalService = Depends(get_signal_service)):
    """
    특정 심볼의 kline 데이터를 조회합니다.
    - **symbol**: BTCUSDT, ETHUSDT 등
    - **limit**: 가져올 데이터 개수 (기본 100개)
    """
    return service.get_klines(symbol=symbol.upper(), limit=limit)

@router.get("/funding-rates/{symbol}", response_model=list[FundingRateBase])
def get_funding_rates_data(symbol: str, limit: int = 100, service: SignalService = Depends(get_signal_service)):
    """
    특정 심볼의 펀딩비 데이터를 조회합니다.
    """
    return service.get_funding_rates(symbol=symbol.upper(), limit=limit)

@router.get("/open-interest/{symbol}", response_model=list[OpenInterestBase])
def get_open_interest_data(symbol: str, limit: int = 100, service: SignalService = Depends(get_signal_service)):
    """
    특정 심볼의 미결제 약정 데이터를 조회합니다.
    """
    return service.get_open_interest(symbol=symbol.upper(), limit=limit)
