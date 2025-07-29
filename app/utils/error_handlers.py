"""
공통 에러 핸들링 유틸리티
"""
import logging
from functools import wraps
from typing import Callable, Any, Dict
from fastapi import HTTPException

from app.utils.helpers import create_api_response

logger = logging.getLogger(__name__)

def handle_api_errors(
    success_message: str = "작업이 성공적으로 완료되었습니다.",
    error_message: str = "작업 중 오류가 발생했습니다."
):
    """
    API 엔드포인트에서 발생하는 공통 오류를 처리하는 데코레이터
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                # 이미 create_api_response 형태라면 그대로 반환
                if isinstance(result, dict) and 'success' in result:
                    return result
                # 그렇지 않다면 성공 형태로 래핑
                return create_api_response(
                    success=True,
                    data=result,
                    message=success_message
                )
            except HTTPException:
                # FastAPI HTTPException은 그대로 재발생
                raise
            except Exception as e:
                logger.error(f"{func.__name__} 실행 중 오류: {str(e)}")
                return create_api_response(
                    success=False,
                    data={},
                    message=f"{error_message}: {str(e)}"
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # 이미 create_api_response 형태라면 그대로 반환
                if isinstance(result, dict) and 'success' in result:
                    return result
                # 그렇지 않다면 성공 형태로 래핑
                return create_api_response(
                    success=True,
                    data=result,
                    message=success_message
                )
            except HTTPException:
                # FastAPI HTTPException은 그대로 재발생
                raise
            except Exception as e:
                logger.error(f"{func.__name__} 실행 중 오류: {str(e)}")
                return create_api_response(
                    success=False,
                    data={},
                    message=f"{error_message}: {str(e)}"
                )
        
        # 함수가 코루틴인지 확인하여 적절한 래퍼 반환
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def handle_service_errors(error_message: str = "서비스 처리 중 오류가 발생했습니다."):
    """
    서비스 레이어에서 발생하는 오류를 처리하는 데코레이터
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} 서비스 오류: {str(e)}")
                raise Exception(f"{error_message}: {str(e)}")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} 서비스 오류: {str(e)}")
                raise Exception(f"{error_message}: {str(e)}")
        
        # 함수가 코루틴인지 확인하여 적절한 래퍼 반환
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class APIErrorHandler:
    """API 에러 핸들링을 위한 헬퍼 클래스"""
    
    @staticmethod
    def handle_validation_error(error: Exception) -> Dict[str, Any]:
        """Pydantic 검증 오류 처리"""
        return create_api_response(
            success=False,
            data={},
            message=f"데이터 검증 오류: {str(error)}"
        )
    
    @staticmethod
    def handle_not_found_error(resource: str) -> Dict[str, Any]:
        """리소스 없음 오류 처리"""
        return create_api_response(
            success=False,
            data={},
            message=f"{resource}을(를) 찾을 수 없습니다."
        )
    
    @staticmethod
    def handle_forbidden_error(action: str) -> Dict[str, Any]:
        """권한 없음 오류 처리"""
        return create_api_response(
            success=False,
            data={},
            message=f"{action}에 대한 권한이 없습니다."
        )
    
    @staticmethod
    def handle_conflict_error(resource: str) -> Dict[str, Any]:
        """충돌 오류 처리"""
        return create_api_response(
            success=False,
            data={},
            message=f"{resource}에서 충돌이 발생했습니다."
        )

# 전역 에러 핸들러 인스턴스
error_handler = APIErrorHandler()
