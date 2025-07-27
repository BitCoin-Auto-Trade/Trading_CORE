"""
응답 캐싱 미들웨어 - 리팩토링된 버전
반복적인 API 요청에 대해 Redis 기반 캐싱 제공
"""

import json
import hashlib
from typing import Optional, Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis
from app.core.db import redis_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """API 응답 캐싱 미들웨어"""
    
    def __init__(
        self, 
        app, 
        default_expire: int = 30,
        cache_config: Optional[Dict[str, int]] = None
    ):
        super().__init__(app)
        self.default_expire = default_expire
        self.redis_client = redis_client
        
        # 캐시 설정 - 외부에서 주입 가능하도록 개선
        self.cache_config = cache_config or {
            "/api/v1/data/realtime/klines": 5,     # K-라인: 5초
            "/api/v1/data/realtime/trades": 10,    # 거래내역: 10초  
            "/api/v1/orders/positions": 30,        # 포지션: 30초
            "/api/v1/orders/account/futures": 60,  # 계정정보: 60초
        }

    async def dispatch(self, request: Request, call_next):
        # GET 요청만 캐싱
        if request.method != "GET":
            return await call_next(request)
        
        # 캐시 대상 경로 확인
        path = request.url.path
        cache_ttl = None
        
        for cached_path, ttl in self.cache_config.items():
            if path.startswith(cached_path):
                cache_ttl = ttl
                break
        
        if cache_ttl is None:
            return await call_next(request)
        
        # 캐시 키 생성 (경로 + 쿼리 파라미터)
        cache_key = self._generate_cache_key(request)
        
        # 캐시된 응답 확인
        try:
            cached_response = self.redis_client.get(cache_key)
            if cached_response:
                cached_data = json.loads(cached_response)
                return Response(
                    content=cached_data["content"],
                    status_code=cached_data["status_code"],
                    headers={
                        "content-type": "application/json",
                        "x-cache": "HIT"
                    }
                )
        except Exception as e:
            logger.warning(f"캐시 조회 실패: {e}")
        
        # 캐시 미스 - 실제 요청 처리
        response = await call_next(request)
        
        # 성공적인 응답만 캐싱
        if response.status_code == 200:
            try:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # 캐시 저장
                cache_data = {
                    "content": response_body.decode(),
                    "status_code": response.status_code
                }
                
                self.redis_client.setex(
                    cache_key, 
                    cache_ttl, 
                    json.dumps(cache_data)
                )
                
                # 새로운 응답 객체 생성
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers={
                        **dict(response.headers),
                        "x-cache": "MISS"
                    }
                )
                
            except Exception as e:
                logger.warning(f"응답 캐싱 실패: {e}")
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """요청에 대한 고유 캐시 키 생성"""
        key_parts = [
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        key_string = "|".join(key_parts)
        return f"api_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
