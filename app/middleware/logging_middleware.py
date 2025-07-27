"""
요청/응답 로깅 미들웨어
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""
    
    def __init__(self, app, log_requests: bool = True, log_responses: bool = False):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청/응답을 로깅합니다."""
        start_time = time.time()
        
        # 요청 로깅 (간소화 - Uvicorn access 로그와 중복 방지)
        if self.log_requests:
            client_ip = self._get_client_ip(request)
            logger.info(
                f"[API] {request.method} {request.url.path} | IP: {client_ip}"
            )
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 시간 계산
        process_time = time.time() - start_time
        
        # 응답 로깅 (에러인 경우만 또는 설정된 경우)
        if self.log_responses or response.status_code >= 400:
            log_level = "ERROR" if response.status_code >= 400 else "INFO"
            message = (
                f"[API] {response.status_code} {request.method} {request.url.path} | "
                f"Time: {process_time:.3f}s"
            )
            
            if log_level == "ERROR":
                logger.error(message)
            else:
                logger.info(message)
        
        # 응답 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = str(round(process_time, 3))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소를 추출합니다."""
        # 프록시를 통한 요청의 경우
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 직접 연결
        if request.client:
            return request.client.host
        
        return "Unknown"
