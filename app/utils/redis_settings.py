"""
Redis 설정 관련 공통 유틸리티 함수들
"""
import json
from typing import Dict, Any
from app.utils.logging import get_logger

logger = get_logger(__name__)


def parse_redis_settings(redis_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Redis에서 가져온 설정 데이터를 적절한 타입으로 파싱합니다.
    
    Args:
        redis_data: Redis에서 가져온 원시 데이터 (문자열 값들)
        
    Returns:
        파싱된 설정 데이터 (적절한 타입으로 변환됨)
    """
    parsed_data = {}
    
    for key, value in redis_data.items():
        # bytes를 문자열로 변환
        key = key.decode() if isinstance(key, bytes) else key
        value = value.decode() if isinstance(value, bytes) else value
        
        try:
            # JSON 파싱 시도 (bool, list, dict 등)
            parsed_value = json.loads(value)
            parsed_data[key] = parsed_value
            logger.debug(f"설정 파싱 성공: {key} = {parsed_value} (타입: {type(parsed_value).__name__})")
        except (json.JSONDecodeError, TypeError):
            # JSON이 아닌 경우 원래 값 사용
            parsed_data[key] = value
            logger.debug(f"설정 원본 사용: {key} = {value} (타입: str)")
    
    return parsed_data


def settings_to_redis_dict(settings_dict: Dict[str, Any]) -> Dict[str, str]:
    """
    설정 딕셔너리를 Redis 저장용 문자열 딕셔너리로 변환합니다.
    
    Args:
        settings_dict: 설정 딕셔너리
        
    Returns:
        Redis 저장용 문자열 딕셔너리
    """
    redis_dict = {}
    
    for key, value in settings_dict.items():
        if isinstance(value, (bool, list, dict)):
            # 복잡한 타입은 JSON으로 변환
            redis_dict[key] = json.dumps(value)
            logger.debug(f"JSON 변환: {key} = {value} -> {redis_dict[key]}")
        else:
            # 단순 타입은 문자열로 변환
            redis_dict[key] = str(value)
            logger.debug(f"문자열 변환: {key} = {value} -> {redis_dict[key]}")
    
    return redis_dict


def safe_type_conversion(value: str, target_type: type, default_value: Any = None) -> Any:
    """
    문자열 값을 안전하게 지정된 타입으로 변환합니다.
    
    Args:
        value: 변환할 문자열 값
        target_type: 변환할 대상 타입
        default_value: 변환 실패시 사용할 기본값
        
    Returns:
        변환된 값 또는 기본값
    """
    try:
        if target_type == bool:
            # bool 타입 특별 처리
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        elif target_type == list:
            # list 타입은 JSON 파싱
            if isinstance(value, list):
                return value
            return json.loads(value)
        elif target_type == dict:
            # dict 타입은 JSON 파싱
            if isinstance(value, dict):
                return value
            return json.loads(value)
        else:
            # 기본 타입 변환
            return target_type(value)
            
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        logger.warning(f"타입 변환 실패: {value} -> {target_type.__name__}, 기본값 사용: {default_value}, 오류: {e}")
        return default_value if default_value is not None else value
