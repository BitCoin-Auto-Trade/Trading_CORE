"""
데이터 조회 관련 API 라우터를 정의하는 모듈입니다.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter
from app.utils.helpers import create_api_response
from app.dependencies import get_binance_adapter, get_db_repository

router = APIRouter()

# --- Realtime Data API --- #

@router.get(
    "/realtime/klines",
    summary="실시간 K-라인 데이터 조회",
    description="실시간 K-라인 데이터를 조회합니다. (프론트엔드 호환성)"
)
def get_realtime_klines(
    symbol: str = Query(..., description="거래 심볼 (예: BTCUSDT)"),
    interval: str = Query("1m", description="시간 간격 (예: 1m, 5m, 1h)"),
    limit: int = Query(1, description="조회할 캔들 개수"),
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter)
):
    """실시간 K-라인 데이터를 조회합니다."""
    if interval == "1m":
        data = binance_adapter.get_kline_1m(symbol.upper())
        return create_api_response(
            success=True,
            data=[data] if data else [],
            message="K-라인 데이터 조회 완료"
        )
    else:
        klines = binance_adapter.client.get_klines(
            symbol=symbol.upper(),
            interval=interval,
            limit=limit
        )
        return create_api_response(
            success=True,
            data=klines,
            message="K-라인 데이터 조회 완료"
        )

@router.get(
    "/realtime/trades",
    summary="실시간 거래 데이터 조회",
    description="실시간 거래 데이터를 조회합니다."
)
def get_realtime_trades(
    symbol: str = Query(..., description="거래 심볼 (예: BTCUSDT)"),
    limit: int = Query(50, description="조회할 거래 개수"),
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter)
):
    """실시간 거래 데이터를 조회합니다."""
    trades = binance_adapter.get_trades(symbol.upper(), limit)
    return create_api_response(
        success=True,
        data=trades,
        message="거래 데이터 조회 완료"
    )

@router.get(
    "/realtime/order-book",
    summary="실시간 오더북 조회",
    description="실시간 오더북 데이터를 조회합니다."
)
def get_realtime_order_book(
    symbol: str = Query(..., description="거래 심볼 (예: BTCUSDT)"),
    limit: int = Query(20, description="조회할 호가 개수"),
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter)
):
    """실시간 오더북 데이터를 조회합니다."""
    order_book = binance_adapter.get_order_book(symbol.upper())
    return create_api_response(
        success=True,
        data=order_book,
        message="오더북 데이터 조회 완료"
    )

# --- Historical Data API --- #

@router.get(
    "/klines",
    summary="K-라인 데이터 조회 (통합)",
    description="데이터베이스에서 K-라인 데이터를 조회합니다."
)
def get_klines_data(
    symbol: str = Query(..., description="거래 심볼 (예: BTCUSDT)"),
    limit: int = Query(100, description="조회할 캔들 개수"),
    db_repository: DBRepository = Depends(get_db_repository)
):
    """데이터베이스에서 K-라인 데이터를 조회합니다."""
    df = db_repository.get_klines_by_symbol_as_df(symbol.upper(), limit)
    
    if df.empty:
        return create_api_response(
            success=True,
            data=[],
            message="조회할 데이터가 없습니다"
        )
    
    # DataFrame을 dict로 변환
    data = []
    for _, row in df.iterrows():
        data.append({
            "symbol": row.get("symbol"),
            "timestamp": row.name,  # index가 timestamp
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "close": float(row.get("close", 0)),
            "volume": float(row.get("volume", 0)),
            # 지표 데이터도 포함
            "atr": float(row.get("atr", 0)) if row.get("atr") is not None else None,
            "ema_20": float(row.get("ema_20", 0)) if row.get("ema_20") is not None else None,
            "sma_50": float(row.get("sma_50", 0)) if row.get("sma_50") is not None else None,
            "sma_200": float(row.get("sma_200", 0)) if row.get("sma_200") is not None else None,
            "rsi_14": float(row.get("rsi_14", 0)) if row.get("rsi_14") is not None else None,
            "macd_hist": float(row.get("macd_hist", 0)) if row.get("macd_hist") is not None else None,
            "stoch_k": float(row.get("stoch_k", 0)) if row.get("stoch_k") is not None else None,
            "stoch_d": float(row.get("stoch_d", 0)) if row.get("stoch_d") is not None else None,
            "bb_upper": float(row.get("bb_upper", 0)) if row.get("bb_upper") is not None else None,
            "bb_lower": float(row.get("bb_lower", 0)) if row.get("bb_lower") is not None else None,
            "adx": float(row.get("adx", 0)) if row.get("adx") is not None else None
        })
    
    return create_api_response(
        success=True,
        data=data,
        message="K-라인 데이터 조회 완료"
    )

@router.get(
    "/historical/trades",
    summary="과거 거래 데이터 조회",
    description="데이터베이스에서 과거 거래 데이터를 조회합니다."
)
def get_historical_trades(
    symbol: str = Query(..., description="거래 심볼 (예: BTCUSDT)"),
    limit: int = Query(100, description="조회할 거래 개수"),
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter)
):
    """데이터베이스에서 과거 거래 데이터를 조회합니다."""
    # 실제 구현 시 데이터베이스에서 조회해야 함
    # 현재는 실시간 데이터로 대체
    trades = binance_adapter.get_trades(symbol.upper(), limit)
    return create_api_response(
        success=True,
        data=trades,
        message="과거 거래 데이터 조회 완료"
    )

@router.get(
    "/historical/funding-rates",
    summary="펀딩비 데이터 조회",
    description="데이터베이스에서 펀딩비 데이터를 조회합니다."
)
def get_historical_funding_rates(
    symbol: str = Query(..., description="거래 심볼 (예: BTCUSDT)"),
    limit: int = Query(100, description="조회할 데이터 개수"),
    db_repository: DBRepository = Depends(get_db_repository)
):
    """데이터베이스에서 펀딩비 데이터를 조회합니다."""
    funding_rates = db_repository.get_funding_rates_by_symbol(symbol.upper(), limit)
    
    data = []
    for rate in funding_rates:
        data.append({
            "symbol": rate.symbol,
            "timestamp": rate.timestamp,
            "funding_rate": float(rate.funding_rate)
        })
    
    return create_api_response(
        success=True,
        data=data,
        message="펀딩비 데이터 조회 완료"
    )

@router.get(
    "/historical/open-interest",
    summary="미결제 약정 데이터 조회",
    description="데이터베이스에서 미결제 약정 데이터를 조회합니다."
)
def get_historical_open_interest(
    symbol: str = Query(..., description="거래 심볼 (예: BTCUSDT)"),
    limit: int = Query(100, description="조회할 데이터 개수"),
    db_repository: DBRepository = Depends(get_db_repository)
):
    """데이터베이스에서 미결제 약정 데이터를 조회합니다."""
    open_interests = db_repository.get_open_interest_by_symbol(symbol.upper(), limit)
    
    data = []
    for oi in open_interests:
        data.append({
            "symbol": oi.symbol,
            "timestamp": oi.timestamp,
            "open_interest": float(oi.open_interest)
        })
    
    return create_api_response(
        success=True,
        data=data,
        message="미결제 약정 데이터 조회 완료"
    )

@router.get(
    "/market-info",
    summary="시장 정보 조회",
    description="시장 정보 및 통계를 조회합니다."
)
def get_market_info(
    symbol: Optional[str] = Query(None, description="거래 심볼 (옵션)"),
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter)
):
    """시장 정보 및 통계를 조회합니다."""
    if symbol:
        # 특정 심볼 정보 조회
        ticker = binance_adapter.client.get_symbol_ticker(symbol=symbol.upper())
        return create_api_response(
            success=True,
            data=ticker,
            message=f"{symbol} 시장 정보 조회 완료"
        )
    else:
        # 전체 시장 정보 조회
        exchange_info = binance_adapter.client.get_exchange_info()
        return create_api_response(
            success=True,
            data=exchange_info,
            message="시장 정보 조회 완료"
        )