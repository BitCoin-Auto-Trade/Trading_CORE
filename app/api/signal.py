from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.signal import SignalService
from app.schemas.signal import TradingSignal

router = APIRouter()

# --- Dependency Injection --- 
def get_signal_service(db: Session = Depends(get_db)) -> SignalService:
    return SignalService(db=db)


@router.get("/trading-signal/rsi/{symbol}", response_model=TradingSignal)
def get_rsi_trading_signal(symbol: str, service: SignalService = Depends(get_signal_service)):
    """
    RSI 값을 기반으로 특정 심볼의 매매 신호를 조회합니다.
    """
    return service.get_trading_signal_by_rsi(symbol.upper())

@router.get("/trading-signal/macd/{symbol}", response_model=TradingSignal)
def get_macd_trading_signal(symbol: str, service: SignalService = Depends(get_signal_service)):
    """
    MACD 값을 기반으로 특정 심볼의 매매 신호를 조회합니다.
    """
    return service.get_trading_signal_by_macd(symbol.upper())

@router.get("/trading-signal/combined/{symbol}", response_model=TradingSignal)
def get_combined_trading_signal(symbol: str, service: SignalService = Depends(get_signal_service)):
    """
    RSI와 MACD를 결합한 종합 매매 신호를 조회합니다.
    """
    return service.get_combined_trading_signal(symbol.upper())
