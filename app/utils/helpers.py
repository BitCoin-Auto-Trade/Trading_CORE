"""
공통 유틸리티 함수 모음

프로젝트 전반에서 사용되는 재사용 가능한 헬퍼 함수들을 제공한다.
- 데이터 변환 및 검증
- API 응답 생성 
- 날짜/시간 처리
- 통화 형식 변환
- 실행 시간 제한 및 재시도 로직
"""
from typing import Any, Dict, Optional, Union, List, Tuple
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import time
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from app.core.constants import ApiResponseStatus, LogLevel
from app.core.exceptions import TimeoutException, ValidationException
from app.utils.logging import get_logger

logger = get_logger(__name__)


def convert_numpy_to_python_types(value: Any) -> Any:
    """NumPy 타입을 Python 기본 타입으로 안전하게 변환
    
    Args:
        value: 변환할 값 (단일 값, 리스트, 딕셔너리 등)
        
    Returns:
        Python 기본 타입으로 변환된 값
    """
    if isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return float(value)
    elif hasattr(np, 'bool_') and isinstance(value, np.bool_):
        return bool(value)
    elif str(type(value)).startswith("<class 'numpy.bool"):
        return bool(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {key: convert_numpy_to_python_types(val) for key, val in value.items()}
    elif isinstance(value, list):
        return [convert_numpy_to_python_types(item) for item in value]
    else:
        return value


def create_standardized_api_response(
    is_success: bool = True,
    message: str = "",
    data: Optional[Any] = None,
    error_code: Optional[str] = None
) -> Dict[str, Any]:
    """표준화된 API 응답 데이터 생성
    
    모든 API 엔드포인트에서 일관된 응답 형식을 제공한다.
    
    Args:
        is_success: 요청 성공 여부
        message: 응답 메시지 
        data: 응답 데이터 (옵션)
        error_code: 에러 코드 (옵션)
        
    Returns:
        표준화된 API 응답 딕셔너리
    """
    response = {
        "success": is_success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = convert_numpy_to_python_types(data)
    
    if error_code:
        response["error_code"] = error_code
    
    return response


def validate_trading_symbol(symbol: str) -> str:
    """거래 심볼 유효성 검증
    
    Args:
        symbol: 검증할 거래 심볼
        
    Returns:
        검증된 거래 심볼 (대문자 변환)
        
    Raises:
        ValidationException: 심볼이 유효하지 않은 경우
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationException("거래 심볼은 비어있을 수 없습니다")
    
    normalized_symbol = symbol.strip().upper()
    if len(normalized_symbol) < 3:
        raise ValidationException("거래 심볼은 최소 3자 이상이어야 합니다")
    
    if not normalized_symbol.isalnum():
        raise ValidationException("거래 심볼은 영문자와 숫자만 포함할 수 있습니다")
    
    return normalized_symbol


def validate_price_value(price: Union[float, str, int]) -> float:
    """가격 값 유효성 검증
    
    Args:
        price: 검증할 가격 값
        
    Returns:
        검증된 가격 (float)
        
    Raises:
        ValidationException: 가격이 유효하지 않은 경우
    """
    try:
        price_float = float(price)
        if price_float <= 0:
            raise ValidationException("가격은 0보다 커야 합니다")
        if price_float > 1e10:  # 너무 큰 값 방지
            raise ValidationException("가격이 너무 큽니다")
        return price_float
    except (ValueError, TypeError) as e:
        raise ValidationException(f"올바른 가격 형식이 아닙니다: {str(e)}")


def validate_quantity_value(quantity: Union[float, str, int]) -> float:
    """수량 값 유효성 검증
    
    Args:
        quantity: 검증할 수량 값
        
    Returns:
        검증된 수량 (float)
        
    Raises:
        ValidationException: 수량이 유효하지 않은 경우
    """
    try:
        quantity_float = float(quantity)
        if quantity_float <= 0:
            raise ValidationException("수량은 0보다 커야 합니다")
        if quantity_float > 1e10:  # 너무 큰 값 방지
            raise ValidationException("수량이 너무 큽니다")
        return quantity_float
    except (ValueError, TypeError) as e:
        raise ValidationException(f"올바른 수량 형식이 아닙니다: {str(e)}")


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """필수 필드 존재 여부 검증
    
    Args:
        data: 검증할 데이터 딕셔너리
        required_fields: 필수 필드 목록
        
    Raises:
        ValidationException: 필수 필드가 누락된 경우
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationException(f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}")


def safe_float_conversion(value: Any, default_value: float = 0.0) -> float:
    """안전한 float 타입 변환
    
    Args:
        value: 변환할 값
        default_value: 변환 실패 시 기본값
        
    Returns:
        변환된 float 값 또는 기본값
    """
    try:
        if value is None:
            return default_value
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Float 변환 실패: {value}, 기본값 {default_value} 사용")
        return default_value


def safe_int_conversion(value: Any, default_value: int = 0) -> int:
    """안전한 int 타입 변환
    
    Args:
        value: 변환할 값
        default_value: 변환 실패 시 기본값
        
    Returns:
        변환된 int 값 또는 기본값
    """
    try:
        if value is None:
            return default_value
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Int 변환 실패: {value}, 기본값 {default_value} 사용")
        return default_value


def safe_bool_conversion(value: Any, default_value: bool = False) -> bool:
    """안전한 bool 타입 변환
    
    Args:
        value: 변환할 값 
        default_value: 변환 실패 시 기본값
        
    Returns:
        변환된 bool 값 또는 기본값
    """
    try:
        if value is None:
            return default_value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    except (ValueError, TypeError):
        return default_value


def format_currency_amount(amount: float, currency: str = "USDT", decimal_places: int = 4) -> str:
    """통화 형식으로 금액 포맷팅
    
    Args:
        amount: 포맷팅할 금액
        currency: 통화 단위
        decimal_places: 소수점 자릿수
        
    Returns:
        포맷팅된 통화 문자열
    """
    return f"{amount:.{decimal_places}f} {currency}"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """퍼센트 변화율 계산
    
    Args:
        old_value: 이전 값
        new_value: 새로운 값
        
    Returns:
        퍼센트 변화율 (-100.0 ~ +무한대)
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    return ((new_value - old_value) / old_value) * 100


def is_within_trading_hours(
    current_time: Optional[datetime] = None,
    trading_hour_ranges: List[Tuple[int, int]] = [(0, 24)]
) -> bool:
    """거래 시간 여부 확인
    
    Args:
        current_time: 확인할 시간 (None이면 현재 시간)
        trading_hour_ranges: 거래 시간 범위 리스트 [(시작시간, 종료시간), ...]
        
    Returns:
        거래 시간 여부
    """
    if current_time is None:
        current_time = datetime.utcnow()
    
    current_hour = current_time.hour
    
    for start_hour, end_hour in trading_hour_ranges:
        if start_hour <= current_hour < end_hour:
            return True
    
    return False


def timeout_decorator(timeout_seconds: int = 30):
    """함수 실행 시간 제한 데코레이터
    
    Args:
        timeout_seconds: 제한 시간 (초)
        
    Returns:
        데코레이터 함수
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise TimeoutException(f"함수 실행 시간 초과: {timeout_seconds}초")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            def timeout_handler(signum, frame):
                raise TimeoutException(f"함수 실행 시간 초과: {timeout_seconds}초")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def retry_on_failure_decorator(max_retries: int = 3, delay_seconds: float = 1.0, backoff_factor: float = 2.0):
    """실패 시 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        delay_seconds: 초기 대기 시간 (초)
        backoff_factor: 대기 시간 증가 배수
        
    Returns:
        데코레이터 함수
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay_seconds * (backoff_factor ** attempt)
                        logger.warning(f"함수 실행 실패 (시도 {attempt + 1}/{max_retries + 1}): {e}, {wait_time}초 후 재시도")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"함수 실행 최종 실패: {e}")
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay_seconds * (backoff_factor ** attempt)
                        logger.warning(f"함수 실행 실패 (시도 {attempt + 1}/{max_retries + 1}): {e}, {wait_time}초 후 재시도")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"함수 실행 최종 실패: {e}")
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def log_execution_time_decorator(func):
    """함수 실행 시간 로깅 데코레이터
    
    Args:
        func: 대상 함수
        
    Returns:
        래핑된 함수
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} 실행 시간: {execution_time:.4f}초")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 실행 실패 (시간: {execution_time:.4f}초): {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} 실행 시간: {execution_time:.4f}초")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 실행 실패 (시간: {execution_time:.4f}초): {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def get_redis_key(key_type: str, *args) -> str:
    """Redis 키 생성 유틸리티 함수
    
    Args:
        key_type: 키 타입 (REDIS_KEY_PATTERNS에서 사용)
        *args: 키에 포함할 추가 인자들
        
    Returns:
        생성된 Redis 키 문자열
    """
    from app.core.constants import REDIS_KEY_PATTERNS
    
    if key_type in REDIS_KEY_PATTERNS:
        base_key = REDIS_KEY_PATTERNS[key_type]
        if args:
            return base_key + ":".join(str(arg) for arg in args)
        return base_key
    else:
        # 하위 호환성을 위해 기본 형식으로 처리
        if args:
            return f"{key_type.lower()}:{':'.join(str(arg) for arg in args)}"
        return key_type.lower()


def chunks_list(input_list: List[Any], chunk_size: int):
    """리스트를 지정된 크기의 청크로 분할
    
    Args:
        input_list: 분할할 리스트
        chunk_size: 청크 크기
        
    Yields:
        청크로 분할된 리스트들
    """
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i:i + chunk_size]


def get_current_utc_timestamp() -> str:
    """현재 UTC 타임스탬프 문자열 반환
    
    Returns:
        ISO 형식의 UTC 타임스탬프 문자열
    """
    return datetime.utcnow().isoformat()


# 하위 호환성을 위한 별칭들과 래퍼 함수들
convert_numpy_types = convert_numpy_to_python_types

def create_api_response(
    success: bool = True,
    message: str = "",
    data: Optional[Any] = None,
    error_code: Optional[str] = None
) -> Dict[str, Any]:
    """하위 호환성을 위한 API 응답 생성 함수"""
    return create_standardized_api_response(
        is_success=success,
        message=message, 
        data=data,
        error_code=error_code
    )

validate_symbol = validate_trading_symbol
validate_price = validate_price_value
validate_quantity = validate_quantity_value
format_currency = format_currency_amount
is_trading_hours = is_within_trading_hours
timeout = timeout_decorator
retry_on_failure = retry_on_failure_decorator
log_execution_time = log_execution_time_decorator
