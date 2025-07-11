"""
데이터 조회 관련 API 라우터를 정의하는 모듈입니다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis

from app.core.db import get_db, get_redis
from app.services.realtime_data_service import RealtimeDataService
from app.services.historical_data_service import HistoricalDataService
from app.schemas.getdata import Kline1mData, OrderBookDepth, TradeData, KlineBase, FundingRateBase, OpenInterestBase

router = APIRouter()

# --- 의존성 주입 --- #

def get_realtime_data_service(redis_client: redis.Redis = Depends(get_redis)) -> RealtimeDataService:
    """ RealtimeDataService 의존성 주입 """
    return RealtimeDataService(redis_client=redis_client)

def get_historical_data_service(db: Session = Depends(get_db)) -> HistoricalDataService:
    """ HistoricalDataService 의존성 주입 """
    return HistoricalDataService(db=db)

# --- 실시간 데이터 API --- #

@router.get("/realtime/kline-1m/{symbol}", response_model=Kline1mData | None, summary="최신 1분봉 캔들 조회")
def get_kline_1m(symbol: str, service: RealtimeDataService = Depends(get_realtime_data_service)):
    """
    특정 심볼의 최신 1분봉 캔들 데이터를 조회합니다.
    - **symbol**: `BTCUSDT`
    """
    return service.get_kline_1m(symbol.upper())

@router.get("/realtime/depth/{symbol}", response_model=OrderBookDepth | None, summary="오더북 조회")
def get_order_book(symbol: str, service: RealtimeDataService = Depends(get_realtime_data_service)):
    """
    특정 심볼의 실시간 오더북(호가창) 데이터를 조회합니다.
    - **symbol**: `BTCUSDT`
    """
    return service.get_order_book(symbol.upper())

@router.get("/realtime/trades/{symbol}", response_model=list[TradeData], summary="최근 체결 내역 조회")
def get_recent_trades(symbol: str, limit: int = 100, service: RealtimeDataService = Depends(get_realtime_data_service)):
    """
    특정 심볼의 최근 체결 내역을 조회합니다.
    - **symbol**: `BTCUSDT`
    - **limit**: 가져올 개수 (기본 100)
    """
    return service.get_trades(symbol.upper(), limit)

# --- 과거 데이터 API --- #

@router.get("/historical/klines/{symbol}", response_model=list[KlineBase], summary="과거 Klines 데이터 조회")
def get_klines_data(symbol: str, limit: int = 100, service: HistoricalDataService = Depends(get_historical_data_service)):
    """
    특정 심볼의 과거 kline 데이터를 DB에서 조회합니다.
    - **symbol**: `BTCUSDT`
    - **limit**: 가져올 개수 (기본 100)
    """
    return service.get_klines_data(symbol=symbol.upper(), limit=limit)

@router.get("/historical/funding-rates/{symbol}", response_model=list[FundingRateBase], summary="과거 펀딩비 조회")
def get_funding_rates_data(symbol: str, limit: int = 100, service: HistoricalDataService = Depends(get_historical_data_service)):
    """
    특정 심볼의 과거 펀딩비 데이터를 DB에서 조회합니다.
    - **symbol**: `BTCUSDT`
    - **limit**: 가져올 개수 (기본 100)
    """
    return service.get_funding_rates_data(symbol=symbol.upper(), limit=limit)

@router.get("/historical/open-interest/{symbol}", response_model=list[OpenInterestBase], summary="과거 미결제 약정 조회")
def get_open_interest_data(symbol: str, limit: int = 100, service: HistoricalDataService = Depends(get_historical_data_service)):
    """
    특정 심볼의 과거 미결제 약정 데이터를 DB에서 조회합니다.
    - **symbol**: `BTCUSDT`
    - **limit**: 가져올 개수 (기본 100)
    """
    return service.get_open_interest_data(symbol=symbol.upper(), limit=limit)
