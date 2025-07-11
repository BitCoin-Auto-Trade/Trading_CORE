"""
주문 관련 API 라우터를 정의하는 모듈입니다.
"""
from fastapi import APIRouter, Depends
import redis

from app.core.db import get_redis
from app.services.order import OrderService
from app.services.realtime_data_service import RealtimeDataService

router = APIRouter()

# --- 의존성 주입 --- #

def get_realtime_data_service(redis_client: redis.Redis = Depends(get_redis)) -> RealtimeDataService:
    """ RealtimeDataService 의존성 주입 """
    return RealtimeDataService(redis_client=redis_client)

def get_order_service(realtime_data_service: RealtimeDataService = Depends(get_realtime_data_service)) -> OrderService:
    """ OrderService 의존성 주입 """
    return OrderService(realtime_data_service=realtime_data_service)

# --- 주문 관련 API (추가 예정) --- #
