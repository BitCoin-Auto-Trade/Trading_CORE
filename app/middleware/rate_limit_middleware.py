"""
간단한 Rate Limiting 미들웨어
동일한 IP에서 과도한 요청을 제한
"""

import time
from typing import Dict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logging import get_logger

logger = get_logger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """간단한 Rate Limiting 미들웨어"""
    
    def __init__(self, app, max_requests: int = 60, time_window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_counts: Dict[str, list] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        
        # 클라이언트 IP별 요청 기록 정리
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # 시간 윈도우 밖의 요청 기록 제거
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if current_time - req_time < self.time_window
        ]
        
        # Rate limit 확인
        if len(self.request_counts[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.time_window} seconds."
            )
        
        # 현재 요청 기록
        self.request_counts[client_ip].append(current_time)
        
        response = await call_next(request)
        return response
