"""
거래 주문 및 포지션 관리 API 라우터

이 모듈은 거래 주문 실행과 포지션 관리와 관련된 API 엔드포인트를 제공합니다.

주요 기능:
- 거래 주문 생성 및 실행
- 활성 포지션 조회 및 관리
- 포지션 모니터링 및 리스크 관리
- 거래 상태 및 통계 조회
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
import redis
import logging

from app.core.db import get_redis
from app.core.config import settings
from app.services.order_service import TradingOrderManager
from app.adapters.binance_adapter import BinanceAdapter
from app.schemas.core import TradingSignal
from app.utils.helpers import create_standardized_api_response, create_api_response  # 하위 호환성
from app.core.dependencies import OrderServiceDep, BinanceAdapterDep, DbRepositoryDep

router = APIRouter()
logger = logging.getLogger(__name__)

# 거래 주문 및 포지션 관리 API 엔드포인트

@router.get("/health")
async def check_order_service_health():
    """주문 서비스 헬스체크 엔드포인트"""
    return create_standardized_api_response(
        is_success=True,
        data={"service_status": "healthy", "service_name": "trading_order_manager"},
        message="거래 주문 관리 서비스가 정상 동작 중입니다."
    )

# 포지션 관리 API 엔드포인트

@router.get(
    "/positions",
    summary="활성 포지션 목록 조회",
    description="현재 관리 중인 모든 활성 포지션의 상세 정보를 조회합니다."
)
async def get_all_active_positions(
    order_service: OrderServiceDep
):
    """활성 포지션 목록 조회 엔드포인트
    
    Returns:
        현재 활성화된 모든 포지션의 요약 정보
    """
    try:
        position_summary = order_service.get_position_summary()
        return position_summary
    except Exception as e:
        logger.error(f"활성 포지션 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"포지션 조회 중 오류 발생: {str(e)}"
        )

@router.delete(
    "/positions/{symbol}",
    summary="특정 포지션 강제 종료",
    description="특정 심볼의 포지션을 강제로 종료합니다."
)
async def force_close_position(
    symbol: str,
    order_service: OrderServiceDep
):
    """특정 포지션을 강제로 종료합니다."""
    try:
        result = await order_service.close_position_by_symbol(symbol)
        return result
    except Exception as e:
        logger.error(f"포지션 강제 종료 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"포지션 강제 종료 중 오류 발생: {str(e)}"
        )

@router.delete(
    "/positions/all",
    summary="모든 포지션 강제 종료",
    description="현재 관리되고 있는 모든 포지션을 강제로 종료합니다."
)
async def force_close_all_positions(
    order_service: OrderServiceDep
):
    """모든 포지션을 강제로 종료합니다."""
    try:
        result = await order_service.close_all_positions()
        return result
    except Exception as e:
        logger.error(f"모든 포지션 강제 종료 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"모든 포지션 강제 종료 중 오류 발생: {str(e)}"
        )

# --- 계정 정보 API --- #

@router.get(
    "/account/futures",
    summary="선물 계정 정보 조회",
    description="바이낸스 선물 계정의 자산, 마진, 잔고 정보를 조회합니다."
)
def get_account_info(
    binance_adapter: BinanceAdapterDep,
    db_repository: DbRepositoryDep
):
    """선물 계정 정보를 조회합니다."""
    try:
        account_info = binance_adapter.get_account_info()
        return create_api_response(
            success=True,
            data=account_info,
            message="계정 정보 조회 완료"
        )
    except Exception as e:
        logger.error(f"선물 계정 정보 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"선물 계정 정보 조회 중 오류 발생: {str(e)}"
        )

@router.get(
    "/account/spot",
    summary="현물 계정 정보 조회",
    description="바이낸스 현물 계정 정보를 조회합니다."
)
def get_spot_account(
    binance_adapter: BinanceAdapterDep
):
    """현물 계정 정보를 조회합니다."""
    try:
        account_info = binance_adapter.client.get_account()
        return create_api_response(
            success=True,
            data=account_info,
            message="현물 계정 정보 조회 완료"
        )
    except Exception as e:
        logger.error(f"현물 계정 정보 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"현물 계정 정보 조회 중 오류 발생: {str(e)}"
        )

# --- 주문 관리 API --- #

@router.get(
    "/open",
    summary="오픈 주문 조회",
    description="현재 오픈된 모든 주문을 조회합니다."
)
def get_open_orders(
    binance_adapter: BinanceAdapterDep,
    symbol: Optional[str] = Query(None, description="특정 심볼 필터링")
):
    """오픈된 주문을 조회합니다."""
    try:
        orders = binance_adapter.get_open_orders(symbol)
        return create_api_response(
            success=True,
            data=orders,
            message="오픈 주문 조회 완료"
        )
    except Exception as e:
        logger.error(f"오픈 주문 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data=[],
            message=f"오픈 주문 조회 중 오류 발생: {str(e)}"
        )

@router.get(
    "/exchange-info",
    summary="거래소 규칙 정보 조회",
    description="거래소에 상장된 선물 심볼들의 거래 규칙을 조회합니다."
)
def get_exchange_info(
    binance_adapter: BinanceAdapterDep
):
    """거래소 규칙 정보를 조회합니다."""
    try:
        info = binance_adapter.get_exchange_info()
        return create_api_response(
            success=True,
            data=info,
            message="거래소 정보 조회 완료"
        )
    except Exception as e:
        logger.error(f"거래소 정보 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"거래소 정보 조회 중 오류 발생: {str(e)}"
        )

# --- 신호 처리 API --- #

@router.post(
    "/process-signal",
    summary="거래 신호 처리",
    description="매매 신호를 기반으로 주문을 실행합니다."
)
async def process_signal(
    signal: TradingSignal,
    order_service: OrderServiceDep
):
    """거래 신호를 처리합니다."""
    try:
        result = await order_service.process_signal(signal)
        return result
    except Exception as e:
        logger.error(f"신호 처리 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"신호 처리 중 오류 발생: {str(e)}"
        )

@router.post(
    "/close/{symbol}",
    summary="특정 포지션 수동 종료",
    description="특정 포지션을 수동으로 종료합니다."
)
async def close_position_manually(
    symbol: str,
    order_service: OrderServiceDep,
    reason: str = Query("MANUAL_CLOSE", description="종료 사유")
):
    """특정 포지션을 수동으로 종료합니다."""
    try:
        result = await order_service.close_position_by_symbol(symbol)
        return result
    except Exception as e:
        logger.error(f"포지션 수동 종료 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"포지션 수동 종료 중 오류 발생: {str(e)}"
        )

# --- 자동 거래 제어 API --- #

@router.post(
    "/auto-trading/toggle",
    summary="자동 거래 토글",
    description="자동 거래 기능을 활성화/비활성화합니다."
)
def toggle_auto_trading(
    enabled: bool = Query(..., description="자동 거래 활성화 여부"),
    redis_client: redis.Redis = Depends(get_redis)
):
    """자동 거래 기능을 토글합니다."""
    try:
        redis_client.set("auto_trading_enabled", str(enabled))
        status = "활성화" if enabled else "비활성화"
        return create_api_response(
            success=True,
            data={"auto_trading_enabled": enabled},
            message=f"자동 거래가 {status}되었습니다."
        )
    except Exception as e:
        logger.error(f"자동 거래 토글 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"자동 거래 토글 중 오류 발생: {str(e)}"
        )

@router.get(
    "/auto-trading/status",
    summary="자동 거래 상태 조회",
    description="현재 자동 거래 상태를 조회합니다."
)
def get_auto_trading_status(
    redis_client: redis.Redis = Depends(get_redis)
):
    """자동 거래 상태를 조회합니다."""
    try:
        enabled_str = redis_client.get("auto_trading_enabled")
        enabled = enabled_str == "True" if enabled_str else settings.TRADING.AUTO_TRADING_ENABLED
        return create_api_response(
            success=True,
            data={"auto_trading_enabled": enabled},
            message=f"자동 거래가 {'활성화' if enabled else '비활성화'}되어 있습니다."
        )
    except Exception as e:
        logger.error(f"자동 거래 상태 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"자동 거래 상태 조회 중 오류 발생: {str(e)}"
        )

# --- 레거시 호환성 API --- #

@router.get(
    "/positions/{symbol}",
    summary="특정 심볼의 포지션 조회",
    description="특정 심볼의 포지션 정보를 조회합니다."
)
async def get_position_by_symbol(
    symbol: str,
    order_service: OrderServiceDep
):
    """특정 심볼의 포지션 정보를 조회합니다."""
    try:
        position = order_service.get_position(symbol)
        if not position:
            raise HTTPException(status_code=404, detail=f"포지션을 찾을 수 없습니다: {symbol}")
        
        return create_api_response(
            success=True,
            data=position.dict(),
            message=f"{symbol} 포지션 조회 완료"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"포지션 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"포지션 조회 중 오류 발생: {str(e)}"
        )
    return create_api_response(
        success=True,
        data={"auto_trading_enabled": enabled},
        message=f"자동 거래가 {status}되었습니다."
    )

@router.get(
    "/auto-trading/status",
    summary="자동 거래 상태 조회",
    description="현재 자동 거래 상태를 조회합니다."
)
def get_auto_trading_status(
    redis_client: redis.Redis = Depends(get_redis)
):
    """자동 거래 상태를 조회합니다."""
    enabled_str = redis_client.get("auto_trading_enabled")
    enabled = enabled_str == "True" if enabled_str else settings.TRADING.AUTO_TRADING_ENABLED
    return create_api_response(
        success=True,
        data={"auto_trading_enabled": enabled},
        message=f"자동 거래가 {'활성화' if enabled else '비활성화'}되어 있습니다."
    )

# --- 레거시 호환성 API --- #

@router.get(
    "/positions/{symbol}",
    summary="특정 심볼의 포지션 조회",
    description="특정 심볼의 포지션 정보를 조회합니다."
)
async def get_position_by_symbol(
    symbol: str,
    order_service: OrderServiceDep
):
    """특정 심볼의 포지션 정보를 조회합니다."""
    try:
        position = order_service.get_position(symbol)
        if not position:
            raise HTTPException(status_code=404, detail=f"포지션을 찾을 수 없습니다: {symbol}")
        
        return create_api_response(
            success=True,
            data=position.dict(),
            message=f"{symbol} 포지션 조회 완료"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"포지션 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"포지션 조회 중 오류 발생: {str(e)}"
        )
