"""
거래 설정 관리 API 라우터 - 완전한 CRUD 지원
"""
import json
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.repository.redis_repository import RedisRepository
from app.core.dependencies import RedisClient
from app.schemas.core import TradingSettings
from app.utils.helpers import create_api_response
from app.utils.logging import get_logger
from app.core.constants import REDIS_KEYS

router = APIRouter()
logger = get_logger(__name__)

SETTINGS_KEY = REDIS_KEYS["TRADING_SETTINGS"]

class SettingUpdateRequest(BaseModel):
    """개별 설정 업데이트를 위한 요청 모델"""
    value: Any

@router.get("/trading")
def get_trading_settings(redis_client: RedisClient):
    """현재 거래 설정을 조회합니다."""
    try:
        settings_data = redis_client.hgetall(SETTINGS_KEY)
        
        if not settings_data:
            logger.info("Redis에 저장된 설정이 없어 기본 설정을 반환합니다.")
            default_settings = TradingSettings()
            return create_api_response(
                success=True,
                data=default_settings.model_dump(),
                message="기본 거래 설정을 반환했습니다."
            )
        
        # Redis에서 가져온 값들을 올바른 타입으로 변환
        parsed_settings = {}
        for key, value in settings_data.items():
            try:
                # JSON으로 파싱 시도 (bool, list, dict 등)
                parsed_settings[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # JSON이 아닌 경우 문자열 그대로 사용
                parsed_settings[key] = value
        
        # Pydantic 모델로 변환하여 타입 검증
        typed_settings = TradingSettings.model_validate(parsed_settings)
        return create_api_response(
            success=True,
            data=typed_settings.model_dump(),
            message="거래 설정을 성공적으로 조회했습니다."
        )
    except Exception as e:
        logger.error(f"거래 설정 조회 실패: {e}")
        return create_api_response(
            success=False,
            data={},
            message=f"거래 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/trading")
def update_trading_settings(
    settings: TradingSettings,
    redis_client: RedisClient
):
    """새로운 거래 설정을 업데이트합니다."""
    try:
        # Pydantic 모델을 dict로 변환하여 Redis에 저장합니다.
        settings_dict = settings.model_dump()
        
        # Redis는 문자열만 저장하므로 복잡한 타입은 JSON으로 변환
        redis_dict = {}
        for key, value in settings_dict.items():
            if isinstance(value, (bool, list, dict)):
                redis_dict[key] = json.dumps(value)
            else:
                redis_dict[key] = str(value)
        
        redis_client.hset(SETTINGS_KEY, mapping=redis_dict)
        
        logger.info(f"거래 설정이 전체 업데이트되었습니다")
        return create_api_response(
            success=True,
            data=settings_dict,
            message="거래 설정이 성공적으로 업데이트되었습니다."
        )
    except Exception as e:
        logger.error(f"거래 설정 업데이트 실패: {e}")
        return create_api_response(
            success=False,
            data={},
            message=f"거래 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@router.patch("/trading/{key}")
def update_single_setting(
    request: SettingUpdateRequest,
    key: str = Path(..., description="업데이트할 설정 키"),
    redis_client: RedisClient = None
):
    """개별 거래 설정을 업데이트합니다."""
    try:
        new_value = request.value
        
        # 현재 설정 가져오기
        current_settings_data = redis_client.hgetall(SETTINGS_KEY)
        if not current_settings_data:
            # 기본 설정으로 초기화
            current_settings = TradingSettings()
            current_settings_data = current_settings.model_dump()
        else:
            # Redis에서 가져온 데이터를 올바른 타입으로 파싱
            parsed_settings = {}
            for key, value in current_settings_data.items():
                try:
                    # JSON으로 파싱 시도 (bool, list, dict 등)
                    parsed_settings[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # JSON이 아닌 경우 문자열 그대로 사용
                    parsed_settings[key] = value
            
            current_settings = TradingSettings.model_validate(parsed_settings)
            current_settings_data = current_settings.model_dump()
        
        # 설정 키가 유효한지 확인
        if key not in current_settings_data:
            available_keys = list(current_settings_data.keys())
            raise HTTPException(
                status_code=400,
                detail=f"유효하지 않은 설정 키입니다. 사용 가능한 키: {available_keys}"
            )
        
        # 기존 값과 타입 확인
        old_value = current_settings_data[key]
        old_type = type(old_value)
        
        # 타입 변환 시도
        try:
            if old_type == bool:
                if isinstance(new_value, str):
                    new_value = new_value.lower() in ('true', '1', 'yes', 'on')
                else:
                    new_value = bool(new_value)
            elif old_type == int:
                new_value = int(new_value)
            elif old_type == float:
                new_value = float(new_value)
            elif old_type == str:
                new_value = str(new_value)
            elif old_type == list:
                if not isinstance(new_value, list):
                    raise ValueError(f"값은 리스트 형태여야 합니다")
            # 다른 타입들은 그대로 유지
        except (ValueError, TypeError) as ve:
            raise HTTPException(
                status_code=400,
                detail=f"타입 변환 실패: {key}는 {old_type.__name__} 타입이어야 합니다. 오류: {str(ve)}"
            )
        
        # 새로운 설정 적용 및 유효성 검사
        current_settings_data[key] = new_value
        try:
            updated_settings = TradingSettings.model_validate(current_settings_data)
        except Exception as validation_error:
            raise HTTPException(
                status_code=400,
                detail=f"설정 유효성 검사 실패: {str(validation_error)}"
            )
        
        # Redis에 저장 (Redis는 문자열만 저장하므로 JSON 문자열로 변환)
        if isinstance(new_value, (bool, list, dict)):
            redis_value = json.dumps(new_value)
        else:
            redis_value = str(new_value)
        
        redis_client.hset(SETTINGS_KEY, key, redis_value)
        
        logger.info(f"설정 '{key}'이 '{old_value}'에서 '{new_value}'로 업데이트되었습니다")
        
        return create_api_response(
            success=True,
            data={
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "updated_settings": updated_settings.model_dump()
            },
            message=f"설정 '{key}'이 성공적으로 업데이트되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"개별 설정 업데이트 실패: {e}")
        return create_api_response(
            success=False,
            data={},
            message=f"설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/trading/reset")
def reset_trading_settings(redis_client: RedisClient):
    """거래 설정을 기본값으로 초기화합니다."""
    try:
        # 현재 설정 백업
        current_settings_data = redis_client.hgetall(SETTINGS_KEY)
        if current_settings_data:
            # Redis에서 가져온 데이터를 올바른 타입으로 파싱
            parsed_settings = {}
            for key, value in current_settings_data.items():
                try:
                    # JSON으로 파싱 시도 (bool, list, dict 등)
                    parsed_settings[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # JSON이 아닌 경우 문자열 그대로 사용
                    parsed_settings[key] = value
            
            current_settings = TradingSettings.model_validate(parsed_settings)
            previous_settings = current_settings.model_dump()
        else:
            previous_settings = {}
        
        # 기본 설정으로 재설정
        default_settings = TradingSettings()
        default_settings_dict = default_settings.model_dump()
        
        # Redis에 기본 설정 저장 (문자열로 변환)
        redis_dict = {}
        for key, value in default_settings_dict.items():
            if isinstance(value, (bool, list, dict)):
                redis_dict[key] = json.dumps(value)
            else:
                redis_dict[key] = str(value)
        
        redis_client.hset(SETTINGS_KEY, mapping=redis_dict)
        
        reset_timestamp = datetime.now()
        
        logger.info("거래 설정이 기본값으로 초기화되었습니다")
        
        return create_api_response(
            success=True,
            data={
                "previous_settings": previous_settings,
                "new_settings": default_settings_dict,
                "reset_timestamp": reset_timestamp.isoformat()
            },
            message="거래 설정이 기본값으로 성공적으로 초기화되었습니다."
        )
        
    except Exception as e:
        logger.error(f"거래 설정 초기화 실패: {e}")
        return create_api_response(
            success=False,
            data={},
            message=f"거래 설정 초기화 중 오류가 발생했습니다: {str(e)}"
        )
