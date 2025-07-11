"""
매매 신호 관련 API 라우터를 정의하는 모듈입니다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis

from app.core.db import get_db, get_redis
from app.services.signal_service import SignalService
from app.services.historical_data_service import HistoricalDataService
from app.services.realtime_data_service import RealtimeDataService
from app.schemas.signal_schema import TradingSignal

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


@router.get("/combined/{symbol}", response_model=TradingSignal, summary="종합 매매 신호 조회")
def get_combined_trading_signal(symbol: str, service: SignalService = Depends(get_signal_service)):
    """
    RSI, MACD, 오더북, 최근 체결 내역을 종합하여 전문적인 매매 신호를 생성합니다.

    - **symbol**: `BTCUSDT`
    - **신호 종류**:
        - `STRONG_BUY`: 강력 매수
        - `BUY`: 매수
        - `HOLD`: 관망
        - `SELL`: 매도
        - `STRONG_SELL`: 강력 매도
    """
    return service.get_combined_trading_signal(symbol.upper())
