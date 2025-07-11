"""
주문 관련 API 라우터를 정의하는 모듈입니다.
"""
from fastapi import APIRouter, Depends, Query
import redis
from typing import Optional, List

from app.core.db import get_redis
from app.services.order_service import OrderService
from app.services.realtime_data_service import RealtimeDataService
from app.services import binance_service
from app.schemas import order_schema

router = APIRouter()

# --- 의존성 주입 --- #

def get_realtime_data_service(redis_client: redis.Redis = Depends(get_redis)) -> RealtimeDataService:
    """ RealtimeDataService 의존성 주입 """
    return RealtimeDataService(redis_client=redis_client)

def get_order_service(realtime_data_service: RealtimeDataService = Depends(get_realtime_data_service)) -> OrderService:
    """ OrderService 의존성 주입 """
    return OrderService(realtime_data_service=realtime_data_service)

# --- 바이낸스 정보 조회 API --- #

@router.get("/account/spot", summary="현물 계좌 정보 조회")
def get_spot_account(testnet: bool = Query(False, description="True이면 테스트넷, False이면 실거래")):
    """ 바이낸스 현물 계좌 정보를 가져옵니다. (필터링되지 않은 원본 데이터) """
    return binance_service.get_account_info(testnet)

@router.get("/account/futures", response_model=order_schema.FuturesAccountInfo, summary="선물 계좌 잔고 및 마진 조회")
def get_futures_account(testnet: bool = Query(False, description="True이면 테스트넷, False이면 실거래")):
    """ 바이낸스 선물 계좌의 자산, 마진, 잔고 정보를 가져옵니다. (잔고 > 0 인 자산만 표시) """
    return binance_service.get_futures_account_balance(testnet)

@router.get("/position", response_model=List[order_schema.PositionInfo], summary="현재 포지션 정보 조회")
def get_position(testnet: bool = Query(False, description="True이면 테스트넷, False이면 실거래")):
    """ 현재 진입해있는 모든 포지션의 상세 정보를 가져옵니다. (포지션이 있는 심볼만 표시) """
    return binance_service.get_position_info(testnet)

@router.get("/orders/open", response_model=List[order_schema.OpenOrderInfo], summary="미체결 주문 내역 조회")
def get_open_orders(symbol: Optional[str] = Query(None, description="특정 심볼 조회 (예: BTCUSDT)"), testnet: bool = Query(False, description="True이면 테스트넷, False이면 실거래")):
    """ 현재 체결되지 않고 대기 중인 모든 주문을 가져옵니다. 특정 심볼만 필터링할 수 있습니다. """
    return binance_service.get_open_orders(symbol, testnet)

@router.get("/exchange-info", response_model=order_schema.ExchangeInfo, summary="거래소 규칙 정보 조회")
def get_exchange_info():
    """ 거래소에 상장된 선물 심볼의 거래 규칙(최소 주문량, 가격/수량 정밀도 등)을 가져옵니다. """
    return binance_service.get_exchange_info()
