from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.signal import SignalService
from app.schemas.signal import KlineBase, FundingRateBase, OpenInterestBase

router = APIRouter()

# --- Dependency Injection --- 
def get_signal_service(db: Session = Depends(get_db)) -> SignalService:
    return SignalService(db=db)


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
