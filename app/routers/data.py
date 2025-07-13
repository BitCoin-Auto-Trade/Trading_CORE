"""
데이터 조회 관련 API 라우터를 정의하는 모듈입니다.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis

from app.core.db import get_db, get_redis
from app.adapters.binance_adapter import BinanceAdapter
from app.schemas.core import (
    Kline1mData,
    OrderBookDepth,
    TradeData,
    KlineBase,
    FundingRateBase,
    OpenInterestBase,
)

router = APIRouter()

# --- Dependency Injection --- #


def get_binance_adapter(
    db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)
) -> BinanceAdapter:
    """
    BinanceAdapter 인스턴스를 의존성 주입합니다.
    """
    return BinanceAdapter(db=db, redis_client=redis_client)


# --- Realtime Data API --- #


@router.get(
    "/realtime/kline-1m/{symbol}",
    response_model=Kline1mData | None,
    summary="Get latest 1-minute kline",
)
def get_kline_1m(
    symbol: str, binance_adapter: BinanceAdapter = Depends(get_binance_adapter)
):
    """
    특정 심볼의 최신 1분봉 캔들 데이터를 조회합니다.
    - **symbol**: 거래 쌍 (예: `BTCUSDT`)
    """
    return binance_adapter.get_kline_1m(symbol.upper())


@router.get(
    "/realtime/depth/{symbol}",
    response_model=OrderBookDepth | None,
    summary="Get order book depth",
)
def get_order_book(
    symbol: str, binance_adapter: BinanceAdapter = Depends(get_binance_adapter)
):
    """
    특정 심볼의 실시간 오더북(호가) 데이터를 조회합니다.
    - **symbol**: 거래 쌍 (예: `BTCUSDT`)
    """
    return binance_adapter.get_order_book(symbol.upper())


@router.get(
    "/realtime/trades/{symbol}",
    response_model=list[TradeData],
    summary="Get recent trades",
)
def get_recent_trades(
    symbol: str,
    limit: int = 100,
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter),
):
    """
    특정 심볼의 최근 체결 내역을 조회합니다.
    - **symbol**: 거래 쌍 (예: `BTCUSDT`)
    - **limit**: 조회할 체결 내역 수 (기본값: 100)
    """
    return binance_adapter.get_trades(symbol.upper(), limit)


# --- Historical Data API --- #


@router.get(
    "/historical/klines/{symbol}",
    response_model=list[KlineBase],
    summary="Get historical klines data",
)
def get_klines_data(
    symbol: str,
    interval: str = "1m",
    limit: int = 100,
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter),
):
    """
    데이터베이스에서 특정 심볼의 과거 캔들 데이터를 조회합니다.
    - **symbol**: 거래 쌍 (예: `BTCUSDT`)
    - **interval**: 캔들 시간 간격 (예: `1m`, `5m`, `1h`)
    - **limit**: 조회할 캔들 수 (기본값: 100)
    """
    return binance_adapter.get_klines_data(
        symbol=symbol.upper(), interval=interval, limit=limit
    )


@router.get(
    "/historical/funding-rates/{symbol}",
    response_model=list[FundingRateBase],
    summary="Get historical funding rates",
)
def get_funding_rates_data(
    symbol: str,
    limit: int = 100,
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter),
):
    """
    데이터베이스에서 특정 심볼의 과거 펀딩비 데이터를 조회합니다.
    - **symbol**: 거래 쌍 (예: `BTCUSDT`)
    - **limit**: 조회할 데이터 수 (기본값: 100)
    """
    return binance_adapter.get_funding_rates_data(symbol=symbol.upper(), limit=limit)


@router.get(
    "/historical/open-interest/{symbol}",
    response_model=list[OpenInterestBase],
    summary="Get historical open interest",
)
def get_open_interest_data(
    symbol: str,
    limit: int = 100,
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter),
):
    """
    데이터베이스에서 특정 심볼의 과거 미결제 약정 데이터를 조회합니다.
    - **symbol**: 거래 쌍 (예: `BTCUSDT`)
    - **limit**: 조회할 데이터 수 (기본값: 100)
    """
    return binance_adapter.get_open_interest_data(symbol=symbol.upper(), limit=limit)
