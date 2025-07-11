"""
매매 신호 관련 API 라우터를 정의하는 모듈입니다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis

from app.core.db import get_db, get_redis
from app.services.signal import SignalService
from app.services.historical_data_service import HistoricalDataService
from app.services.realtime_data_service import RealtimeDataService
from app.schemas.signal import TradingSignal

router = APIRouter()

# --- 의존성 주입 --- #

def get_historical_data_service(db: Session = Depends(get_db)) -> HistoricalDataService:
    """ HistoricalDataService 의존성 주입 """
    return HistoricalDataService(db=db)

def get_realtime_data_service(redis_client: redis.Redis = Depends(get_redis)) -> RealtimeDataService:
    """ RealtimeDataService 의존성 주입 """
    return RealtimeDataService(redis_client=redis_client)

def get_signal_service(
    historical_data_service: HistoricalDataService = Depends(get_historical_data_service),
    realtime_data_service: RealtimeDataService = Depends(get_realtime_data_service)
) -> SignalService:
    """ SignalService 의존성 주입 """
    return SignalService(historical_data_service=historical_data_service, realtime_data_service=realtime_data_service)


@router.get("/rsi/{symbol}", response_model=TradingSignal, summary="RSI 기반 매매 신호 조회")
def get_rsi_trading_signal(symbol: str, service: SignalService = Depends(get_signal_service)):
    """
    RSI 값을 기반으로 특정 심볼의 매매 신호를 조회합니다.
    - **symbol**: `BTCUSDT`
    """
    return service.get_trading_signal_by_rsi(symbol.upper())

@router.get("/macd/{symbol}", response_model=TradingSignal, summary="MACD 기반 매매 신호 조회")
def get_macd_trading_signal(symbol: str, service: SignalService = Depends(get_signal_service)):
    """
    MACD 값을 기반으로 특정 심볼의 매매 신호를 조회합니다.
    - **symbol**: `BTCUSDT`
    """
    return service.get_trading_signal_by_macd(symbol.upper())

@router.get("/combined/{symbol}", response_model=TradingSignal, summary="RSI & MACD 종합 매매 신호 조회")
def get_combined_trading_signal(symbol: str, service: SignalService = Depends(get_signal_service)):
    """
    RSI와 MACD를 결합한 종합 매매 신호를 조회합니다.
    - **symbol**: `BTCUSDT`
    """
    return service.get_combined_trading_signal(symbol.upper())
