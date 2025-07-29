"""
트레이딩 신호 API 라우터

이 모듈은 거래 신호 생성 및 조회와 관련된 API 엔드포인트를 제공합니다.

주요 기능:
- 실시간 거래 신호 생성 및 조회
- 신호 이력 관리 및 통계
- 신호 서비스 상태 모니터링
- 성과 지표 추적
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import json
import logging

from app.services.signal_service import TradingSignalAnalyzer
from app.utils.helpers import create_standardized_api_response, create_api_response  # 하위 호환성
from app.core.dependencies import SignalServiceDep

router = APIRouter()
logger = logging.getLogger(__name__)

# 트레이딩 신호 관련 API 엔드포인트

@router.get(
    "/health",
    summary="신호 서비스 헬스체크",
    description="트레이딩 신호 서비스의 상태와 가용성을 확인합니다."
)
async def check_signal_service_health():
    """신호 서비스 상태 확인 엔드포인트"""
    return create_standardized_api_response(
        is_success=True,
        data={"service_status": "healthy", "service_name": "trading_signal_analyzer"},
        message="트레이딩 신호 서비스가 정상 동작 중입니다."
    )

@router.get(
    "/latest",
    summary="최신 거래 신호 조회",
    description="지정된 심볼의 최신 거래 신호를 생성하고 반환합니다."
)
async def get_latest_trading_signal(
    signal_service: SignalServiceDep,
    symbol: Optional[str] = None
):
    """최신 거래 신호 조회 엔드포인트
    
    Args:
        symbol: 거래 심볼 (기본값: BTCUSDT)
        
    Returns:
        최신 거래 신호 정보
    """
    try:
        target_symbol = symbol.upper() if symbol else "BTCUSDT"
        signal = signal_service.generate_comprehensive_trading_signal(target_symbol)
        
        # 신호 객체를 딕셔너리로 변환
        signal_dict = signal.dict() if hasattr(signal, 'dict') else signal
        
        response_data = create_api_response(
            success=True,
            data=signal_dict,
            message="최신 신호 조회 완료"
        )
        
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error(f"최신 거래 신호 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"최신 거래 신호 조회 실패: {str(e)}"
        )

@router.get(
    "/comprehensive/{symbol}",
    summary="종합 거래 신호 조회",
    description="지정된 심볼의 다중 타임프레임 분석 기반 종합 거래 신호를 조회합니다."
)
async def get_comprehensive_signal_for_symbol(
    symbol: str,
    signal_service: SignalServiceDep
):
    """종합 거래 신호 조회 엔드포인트
    
    Args:
        symbol: 분석할 거래 심볼
        
    Returns:
        종합 분석된 거래 신호
    """
    try:
        signal = signal_service.generate_comprehensive_trading_signal(symbol.upper())
        
        # 신호 객체를 딕셔너리로 변환
        signal_dict = signal.dict() if hasattr(signal, 'dict') else signal
        
        response_data = create_api_response(
            success=True,
            data=signal_dict,
            message=f"{symbol} 종합 거래 신호 분석 완료"
        )
        
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error(f"통합 신호 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"통합 신호 조회 중 오류 발생: {str(e)}"
        )

@router.post(
    "/generate/{symbol}",
    summary="거래 신호 생성",
    description="지정된 심볼에 대한 새로운 거래 신호를 즉시 생성합니다."
)
async def generate_new_trading_signal(
    symbol: str,
    signal_service: SignalServiceDep
):
    """새로운 거래 신호 생성 엔드포인트
    
    Args:
        symbol: 신호를 생성할 거래 심볼
        
    Returns:
        새로 생성된 거래 신호
    """
    try:
        signal = signal_service.generate_comprehensive_trading_signal(symbol.upper())
        
        # 신호 객체를 딕셔너리로 변환
        signal_dict = signal.dict() if hasattr(signal, 'dict') else signal
        
        response_data = create_api_response(
            success=True,
            data=signal_dict,
            message=f"{symbol} 거래 신호 생성 완료"
        )
        
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error(f"거래 신호 생성 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"거래 신호 생성 실패: {str(e)}"
        )

@router.get(
    "/cached",
    summary="캐시된 신호 조회",
    description="Redis에 캐시된 신호들을 조회합니다."
)
def get_cached_signals(
    signal_service: SignalServiceDep,
    symbol: Optional[str] = None
):
    """캐시된 신호들을 조회합니다."""
    try:
        # 현재 구현에서는 Redis 캐시된 신호 대신 최신 신호 반환
        if symbol:
            signals = signal_service.get_combined_trading_signal(symbol.upper())
        else:
            signals = signal_service.get_combined_trading_signal("BTCUSDT")
        
        # signals을 dict로 변환
        signals_dict = signals.dict() if hasattr(signals, 'dict') else signals
        
        response_data = create_api_response(
            success=True,
            data=signals_dict,
            message="캐시된 신호 조회 완료"
        )
        
        return JSONResponse(content=response_data)
    except Exception as e:
        logger.error(f"캐시된 신호 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"캐시된 신호 조회 중 오류 발생: {str(e)}"
        )

@router.get(
    "/performance",
    summary="신호 성과 지표 조회",
    description="거래 신호의 성과 통계와 승률을 조회합니다."
)
async def get_trading_signal_performance(
    signal_service: SignalServiceDep,
    symbol: Optional[str] = None,
    period_days: int = 30
):
    """거래 신호 성과 지표 조회 엔드포인트
    
    Args:
        symbol: 특정 심볼 성과 조회 (옵션)
        period_days: 조회 기간 (일)
        
    Returns:
        신호 성과 통계 정보
    """
    try:
        performance_metrics = signal_service.get_current_performance_metrics()
        return performance_metrics
    except Exception as e:
        logger.error(f"거래 신호 성과 지표 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data={},
            message=f"성과 지표 조회 실패: {str(e)}"
        )

@router.get(
    "/history",
    summary="신호 이력 조회",
    description="과거 생성된 거래 신호의 이력을 조회합니다."
)
async def get_trading_signal_history(
    signal_service: SignalServiceDep,
    symbol: Optional[str] = None,
    limit: int = 100
):
    """거래 신호 이력 조회 엔드포인트
    
    Args:
        symbol: 특정 심볼 이력 필터 (옵션)
        limit: 조회할 최대 개수
        
    Returns:
        거래 신호 이력 목록
    """
    try:
        # 신호 이력 버퍼에서 최근 기록 반환
        history_buffer = signal_service.signal_history_buffer
        recent_history = list(history_buffer)[-limit:] if limit > 0 else list(history_buffer)
        
        # 심볼 필터링 적용
        if symbol:
            filtered_history = [h for h in recent_history if h.get('symbol') == symbol.upper()]
            recent_history = filtered_history
        
        return create_api_response(
            success=True,
            data=recent_history,
            message=f"거래 신호 이력 조회 완료 ({len(recent_history)}개)"
        )
    except Exception as e:
        logger.error(f"거래 신호 이력 조회 중 오류: {str(e)}")
        return create_api_response(
            success=False,
            data=[],
            message=f"신호 이력 조회 실패: {str(e)}"
        )