"""
공통으로 사용되는 유틸리티 함수들을 제공합니다.
"""
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import time
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from app.core.constants import API_STATUS, LOG_LEVELS
from app.core.exceptions import TimeoutException, ValidationException
from app.utils.logging import get_logger

logger = get_logger(__name__)


def convert_numpy_types(obj):
    """numpy 타입을 Python 기본 타입으로 변환합니다."""
    from datetime import datetime
    
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif hasattr(np, 'bool_') and isinstance(obj, np.bool_):
        return bool(obj)
    elif str(type(obj)).startswith("<class 'numpy.bool"):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


def create_api_response(
    success: bool = True,
    message: str = "",
    data: Optional[Any] = None,
    error_code: Optional[str] = None
) -> Dict[str, Any]:
    """표준화된 API 응답을 생성합니다."""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = convert_numpy_types(data)
    
    if error_code:
        response["error_code"] = error_code
    
    return response


def validate_symbol(symbol: str) -> str:
    """거래 심볼의 유효성을 검사합니다."""
    if not symbol or not isinstance(symbol, str):
        raise ValidationException("심볼은 비어있을 수 없습니다")
    
    symbol = symbol.strip().upper()
    if len(symbol) < 3:
        raise ValidationException("심볼은 최소 3자 이상이어야 합니다")
    
    if not symbol.isalnum():
        raise ValidationException("심볼은 알파벳과 숫자만 포함할 수 있습니다")
    
    return symbol


def validate_price(price: Union[float, str]) -> float:
    """가격의 유효성을 검사합니다."""
    try:
        price_float = float(price)
        if price_float <= 0:
            raise ValidationException("가격은 0보다 커야 합니다")
        return price_float
    except (ValueError, TypeError):
        raise ValidationException("올바른 가격 형식이 아닙니다")


def validate_quantity(quantity: Union[float, str]) -> float:
    """수량의 유효성을 검사합니다."""
    try:
        quantity_float = float(quantity)
        if quantity_float <= 0:
            raise ValidationException("수량은 0보다 커야 합니다")
        return quantity_float
    except (ValueError, TypeError):
        raise ValidationException("올바른 수량 형식이 아닙니다")


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """필수 필드가 모두 존재하는지 확인합니다."""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationException(f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}")


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """안전하게 float으로 변환합니다."""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """안전한 int 변환을 수행합니다."""
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Int 변환 실패: {value}, 기본값 {default} 사용")
        return default


def safe_bool_conversion(value: Any, default: bool = False) -> bool:
    """안전하게 bool으로 변환합니다."""
    try:
        if value is None:
            return default
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    except (ValueError, TypeError):
        return default


def format_currency(amount: float, currency: str = "USDT", decimals: int = 4) -> str:
    """통화 형식으로 포맷팅합니다."""
    return f"{amount:.{decimals}f} {currency}"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """퍼센트 변화율을 계산합니다."""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def is_trading_hours(
    current_time: Optional[datetime] = None,
    trading_hours: list = [(9, 24), (0, 2)]
) -> bool:
    """거래 시간인지 확인합니다."""
    if current_time is None:
        current_time = datetime.now()
    
    current_hour = current_time.hour
    
    for start, end in trading_hours:
        if start <= end:
            if start <= current_hour < end:
                return True
        else:  # 자정을 넘어가는 경우
            if current_hour >= start or current_hour < end:
                return True
    
    return False


def timeout(timeout_seconds: int = 30):
    """함수 실행 시간 제한을 설정하는 데코레이터"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                except asyncio.TimeoutError:
                    raise TimeoutException(f"함수 {func.__name__} 실행 시간이 {timeout_seconds}초를 초과했습니다")
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                def handler(signum, frame):
                    raise TimeoutException(f"함수 {func.__name__} 실행 시간이 {timeout_seconds}초를 초과했습니다")
                
                # 타임아웃 설정
                old_handler = signal.signal(signal.SIGALRM, handler)
                signal.alarm(timeout_seconds)
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            return sync_wrapper
    return decorator


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """실패 시 재시도 로직을 제공하는 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"함수 {func.__name__} 실행 실패 (시도 {attempt + 1}/{max_retries + 1}): {str(e)}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"함수 {func.__name__} 최대 재시도 횟수 초과: {str(e)}")
                        raise last_exception
            
            raise last_exception
        return wrapper
    return decorator

def log_execution_time(func):
    """함수 실행 시간을 로깅하는 데코레이터"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} 실행 시간: {execution_time:.3f}초")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 실행 실패 (시간: {execution_time:.3f}초): {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} 실행 시간: {execution_time:.3f}초")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 실행 실패 (시간: {execution_time:.3f}초): {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def get_redis_key(prefix: str, *args) -> str:
    """Redis 키를 생성합니다."""
    if not args:
        return prefix.rstrip(':')
    return f"{prefix}{':'.join(str(arg) for arg in args)}"


def chunk_list(lst: list, chunk_size: int) -> list:
    """리스트를 지정된 크기로 나눕니다."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: dict) -> dict:
    """여러 딕셔너리를 병합합니다."""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def clean_none_values(data: dict) -> dict:
    """딕셔너리에서 None 값을 제거합니다."""
    return {k: v for k, v in data.items() if v is not None}