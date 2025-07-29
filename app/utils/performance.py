"""
성능 최적화를 위한 캐싱 유틸리티
"""
import json
import pickle
import hashlib
from typing import Any, Optional, Callable, Union
from functools import wraps
import redis
from datetime import datetime, timedelta

from app.utils.logging import get_logger

logger = get_logger(__name__)

class CacheManager:
    """Redis 기반 캐시 관리자"""
    
    def __init__(self, redis_client: redis.Redis, default_ttl: int = 300):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = "cache:"
    
    def _generate_key(self, namespace: str, key_data: Any) -> str:
        """캐시 키 생성"""
        if isinstance(key_data, (dict, list)):
            key_str = json.dumps(key_data, sort_keys=True)
        else:
            key_str = str(key_data)
        
        # 키가 너무 길면 해시 사용
        if len(key_str) > 200:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{self.key_prefix}{namespace}:{key_hash}"
        
        return f"{self.key_prefix}{namespace}:{key_str}"
    
    def get(self, namespace: str, key: Any, serialization: str = "json") -> Optional[Any]:
        """캐시에서 데이터 조회"""
        try:
            cache_key = self._generate_key(namespace, key)
            cached_data = self.redis.get(cache_key)
            
            if cached_data is None:
                return None
            
            if serialization == "json":
                return json.loads(cached_data)
            elif serialization == "pickle":
                return pickle.loads(cached_data)
            else:
                return cached_data.decode('utf-8')
                
        except Exception as e:
            logger.warning(f"캐시 조회 실패: {namespace}:{key} - {e}")
            return None
    
    def set(self, namespace: str, key: Any, value: Any, ttl: Optional[int] = None, serialization: str = "json") -> bool:
        """캐시에 데이터 저장"""
        try:
            cache_key = self._generate_key(namespace, key)
            ttl = ttl or self.default_ttl
            
            if serialization == "json":
                serialized_data = json.dumps(value, default=str)
            elif serialization == "pickle":
                serialized_data = pickle.dumps(value)
            else:
                serialized_data = str(value)
            
            return self.redis.setex(cache_key, ttl, serialized_data)
            
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {namespace}:{key} - {e}")
            return False
    
    def delete(self, namespace: str, key: Any) -> bool:
        """캐시에서 데이터 삭제"""
        try:
            cache_key = self._generate_key(namespace, key)
            return bool(self.redis.delete(cache_key))
        except Exception as e:
            logger.warning(f"캐시 삭제 실패: {namespace}:{key} - {e}")
            return False
    
    def clear_namespace(self, namespace: str) -> int:
        """특정 네임스페이스의 모든 캐시 삭제"""
        try:
            pattern = f"{self.key_prefix}{namespace}:*"
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"네임스페이스 캐시 삭제 실패: {namespace} - {e}")
            return 0

def cached(
    namespace: str, 
    ttl: int = 300, 
    serialization: str = "json",
    key_generator: Optional[Callable] = None
):
    """
    함수 결과를 캐싱하는 데코레이터
    
    Args:
        namespace: 캐시 네임스페이스
        ttl: TTL in seconds
        serialization: 직렬화 방법 ("json", "pickle", "string")
        key_generator: 커스텀 키 생성 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Redis 클라이언트 가져오기
            try:
                from app.core.db import redis_client
                cache_manager = CacheManager(redis_client, ttl)
            except Exception as e:
                logger.warning(f"캐시 매니저 초기화 실패: {e}")
                return await func(*args, **kwargs)
            
            # 캐시 키 생성
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 캐시에서 조회
            cached_result = cache_manager.get(namespace, cache_key, serialization)
            if cached_result is not None:
                logger.debug(f"캐시 히트: {namespace}:{cache_key}")
                return cached_result
            
            # 함수 실행 및 결과 캐싱
            result = await func(*args, **kwargs)
            cache_manager.set(namespace, cache_key, result, ttl, serialization)
            logger.debug(f"캐시 저장: {namespace}:{cache_key}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Redis 클라이언트 가져오기
            try:
                from app.core.db import redis_client
                cache_manager = CacheManager(redis_client, ttl)
            except Exception as e:
                logger.warning(f"캐시 매니저 초기화 실패: {e}")
                return func(*args, **kwargs)
            
            # 캐시 키 생성
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 캐시에서 조회
            cached_result = cache_manager.get(namespace, cache_key, serialization)
            if cached_result is not None:
                logger.debug(f"캐시 히트: {namespace}:{cache_key}")
                return cached_result
            
            # 함수 실행 및 결과 캐싱
            result = func(*args, **kwargs)
            cache_manager.set(namespace, cache_key, result, ttl, serialization)
            logger.debug(f"캐시 저장: {namespace}:{cache_key}")
            
            return result
        
        # 함수가 코루틴인지 확인하여 적절한 래퍼 반환
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class PerformanceMonitor:
    """성능 모니터링 유틸리티"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.metrics_key = "performance_metrics"
    
    def record_execution_time(self, function_name: str, execution_time: float):
        """함수 실행 시간 기록"""
        try:
            timestamp = datetime.now().isoformat()
            metric_data = {
                "function": function_name,
                "execution_time": execution_time,
                "timestamp": timestamp
            }
            
            # 최근 1000개 메트릭만 유지
            self.redis.lpush(self.metrics_key, json.dumps(metric_data))
            self.redis.ltrim(self.metrics_key, 0, 999)
            
        except Exception as e:
            logger.warning(f"성능 메트릭 기록 실패: {e}")
    
    def get_performance_stats(self, function_name: Optional[str] = None) -> dict:
        """성능 통계 조회"""
        try:
            metrics = self.redis.lrange(self.metrics_key, 0, -1)
            data = [json.loads(metric) for metric in metrics]
            
            if function_name:
                data = [d for d in data if d["function"] == function_name]
            
            if not data:
                return {"message": "데이터 없음"}
            
            execution_times = [d["execution_time"] for d in data]
            
            return {
                "count": len(execution_times),
                "avg_time": sum(execution_times) / len(execution_times),
                "min_time": min(execution_times),
                "max_time": max(execution_times),
                "last_execution": data[0]["timestamp"] if data else None
            }
            
        except Exception as e:
            logger.error(f"성능 통계 조회 실패: {e}")
            return {"error": str(e)}

def monitor_performance(function_name: Optional[str] = None):
    """함수 실행 시간을 모니터링하는 데코레이터"""
    def decorator(func: Callable) -> Callable:
        name = function_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = (datetime.now() - start_time).total_seconds()
                try:
                    from app.core.db import redis_client
                    monitor = PerformanceMonitor(redis_client)
                    monitor.record_execution_time(name, execution_time)
                except Exception as e:
                    logger.warning(f"성능 모니터링 실패: {e}")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = (datetime.now() - start_time).total_seconds()
                try:
                    from app.core.db import redis_client
                    monitor = PerformanceMonitor(redis_client)
                    monitor.record_execution_time(name, execution_time)
                except Exception as e:
                    logger.warning(f"성능 모니터링 실패: {e}")
        
        # 함수가 코루틴인지 확인하여 적절한 래퍼 반환
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
