"""
에러 핸들링 미들웨어
"""
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import TradingCoreException
from app.utils.helpers import create_api_response
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """전역 에러 핸들링 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 중 발생하는 모든 예외를 처리합니다."""
        try:
            response = await call_next(request)
            return response
            
        except TradingCoreException as e:
            # 비즈니스 로직 예외
            logger.warning(
                f"Business Exception - URL: {request.url} | "
                f"Method: {request.method} | "
                f"Error: {str(e)}"
            )
            
            return JSONResponse(
                status_code=400,
                content=create_api_response(
                    success=False,
                    message=str(e),
                    error_code=e.__class__.__name__
                )
            )
            
        except ValueError as e:
            # 값 오류 (잘못된 파라미터 등)
            logger.warning(
                f"Value Error - URL: {request.url} | "
                f"Method: {request.method} | "
                f"Error: {str(e)}"
            )
            
            return JSONResponse(
                status_code=422,
                content=create_api_response(
                    success=False,
                    message=f"잘못된 요청 파라미터: {str(e)}",
                    error_code="VALIDATION_ERROR"
                )
            )
            
        except Exception as e:
            # 예상치 못한 서버 오류
            error_trace = traceback.format_exc()
            logger.error(
                f"Unexpected Error - URL: {request.url} | "
                f"Method: {request.method} | "
                f"Error: {str(e)} | "
                f"Trace: {error_trace}"
            )
            
            return JSONResponse(
                status_code=500,
                content=create_api_response(
                    success=False,
                    message="서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    error_code="INTERNAL_SERVER_ERROR"
                )
            )
