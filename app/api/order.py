from fastapi import APIRouter, Depends
import redis

from app.core.db import get_redis
from app.services.order import OrderService

router = APIRouter()

# --- Dependency Injection --- 
def get_order_service(redis_client: redis.Redis = Depends(get_redis)) -> OrderService:
    return OrderService(redis_client=redis_client)
