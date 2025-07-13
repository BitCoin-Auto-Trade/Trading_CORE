"""
주문 관련 API 라우터를 정의하는 모듈입니다.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import redis
from typing import Optional, List, Any

from app.core.db import get_db, get_redis
from app.services.order_service import OrderService
from app.adapters.binance_adapter import BinanceAdapter
from app.schemas import core as schemas

router = APIRouter()

# --- Dependency Injection --- #


def get_binance_adapter(
    db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)
) -> BinanceAdapter:
    """
    Injects a BinanceAdapter instance.
    """
    return BinanceAdapter(db=db, redis_client=redis_client)


def get_order_service(
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter),
) -> OrderService:
    """
    Injects an OrderService instance.
    """
    return OrderService(binance_adapter=binance_adapter)


# --- 바이낸스 정보 조회 API --- #


@router.get("/account/spot", response_model=Any, summary="Get spot account info")
def get_spot_account(binance_adapter: BinanceAdapter = Depends(get_binance_adapter)):
    """
    바이낸스 현물 계좌 정보를 조회합니다. (필터링되지 않은 원본 데이터)
    """
    return binance_adapter.client.get_account()


@router.get(
    "/account/futures",
    response_model=schemas.FuturesAccountInfo,
    summary="Get futures account balance and margin",
)
def get_futures_account(binance_adapter: BinanceAdapter = Depends(get_binance_adapter)):
    """
    바이낸스 선물 계좌의 자산, 마진, 잔고 정보를 조회합니다. (잔고가 0보다 큰 자산만 필터링)
    """
    return binance_adapter.get_futures_account_balance()


@router.get(
    "/position",
    response_model=List[schemas.PositionInfo],
    summary="Get current position info",
)
def get_position(binance_adapter: BinanceAdapter = Depends(get_binance_adapter)):
    """
    현재 보유 중인 모든 포지션의 상세 정보를 조회합니다. (포지션이 있는 심볼만 필터링)
    """
    return binance_adapter.get_position_info()


@router.get(
    "/open", response_model=List[schemas.OpenOrderInfo], summary="Get open orders"
)
def get_open_orders(
    symbol: Optional[str] = Query(
        None, description="Filter by specific symbol (e.g., BTCUSDT)"
    ),
    binance_adapter: BinanceAdapter = Depends(get_binance_adapter),
):
    """
    현재 오픈된 모든 주문을 조회합니다. 특정 심볼로 필터링할 수 있습니다.
    """
    return binance_adapter.get_open_orders(symbol)


@router.get(
    "/exchange-info",
    response_model=schemas.ExchangeInfo,
    summary="Get exchange rules info",
)
def get_exchange_info(binance_adapter: BinanceAdapter = Depends(get_binance_adapter)):
    """
    거래소에 상장된 선물 심볼들의 거래 규칙(최소 주문 수량, 가격/수량 정밀도 등)을 조회합니다.
    """
    return binance_adapter.get_exchange_info()
