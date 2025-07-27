"""
신호 관련 API 라우터를 정의하는 모듈입니다.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import json

from app.services.signal_service import SignalService
from app.utils.helpers import create_api_response
from app.dependencies import get_signal_service

router = APIRouter()

# --- 신호 관리 API --- #

@router.get(
    "/health",
    summary="신호 서비스 상태 확인",
    description="신호 서비스의 상태를 확인합니다."
)
def health_check():
    """신호 서비스 상태를 확인합니다."""
    return create_api_response(
        success=True,
        data={"status": "healthy"},
        message="신호 서비스가 정상 동작 중입니다."
    )

@router.get(
    "/latest",
    summary="최신 신호 조회",
    description="가장 최근의 거래 신호를 조회합니다."
)
def get_latest_signal(
    symbol: Optional[str] = None,
    signal_service: SignalService = Depends(get_signal_service)
):
    """최신 신호를 조회합니다."""
    if symbol:
        signal = signal_service.get_combined_trading_signal(symbol.upper())
    else:
        signal = signal_service.get_combined_trading_signal("BTCUSDT")  # 기본값
    
    # signal을 dict로 변환
    signal_dict = signal.dict() if hasattr(signal, 'dict') else signal
    
    response_data = create_api_response(
        success=True,
        data=signal_dict,
        message="최신 신호 조회 완료"
    )
    
    return JSONResponse(content=response_data)

@router.get(
    "/combined/{symbol}",
    summary="통합 신호 조회",
    description="특정 심볼의 통합 거래 신호를 조회합니다."
)
def get_combined_signal(
    symbol: str,
    signal_service: SignalService = Depends(get_signal_service)
):
    """통합 신호를 조회합니다."""
    signal = signal_service.get_combined_trading_signal(symbol.upper())
    
    # signal을 dict로 변환
    signal_dict = signal.dict() if hasattr(signal, 'dict') else signal
    
    response_data = create_api_response(
        success=True,
        data=signal_dict,
        message=f"{symbol} 통합 신호 조회 완료"
    )
    
    return JSONResponse(content=response_data)

@router.post(
    "/generate/{symbol}",
    summary="신호 생성",
    description="특정 심볼에 대한 새로운 거래 신호를 생성합니다."
)
def generate_signal(
    symbol: str,
    signal_service: SignalService = Depends(get_signal_service)
):
    """새로운 신호를 생성합니다."""
    signal = signal_service.get_combined_trading_signal(symbol.upper())
    
    # signal을 dict로 변환
    signal_dict = signal.dict() if hasattr(signal, 'dict') else signal
    
    response_data = create_api_response(
        success=True,
        data=signal_dict,
        message=f"{symbol} 신호 생성 완료"
    )
    
    return JSONResponse(content=response_data)

@router.get(
    "/cached",
    summary="캐시된 신호 조회",
    description="Redis에 캐시된 신호들을 조회합니다."
)
def get_cached_signals(
    symbol: Optional[str] = None,
    signal_service: SignalService = Depends(get_signal_service)
):
    """캐시된 신호들을 조회합니다."""
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

@router.get(
    "/performance",
    summary="신호 성과 분석",
    description="신호의 성과를 분석합니다."
)
def get_signal_performance(
    symbol: Optional[str] = None,
    days: int = 30,
    signal_service: SignalService = Depends(get_signal_service)
):
    """신호 성과를 분석합니다."""
    performance = signal_service.get_performance_stats()
    return create_api_response(
        success=True,
        data=performance,
        message="신호 성과 분석 완료"
    )

@router.get(
    "/history",
    summary="신호 기록 조회",
    description="과거 신호 기록을 조회합니다."
)
def get_signal_history(
    symbol: Optional[str] = None,
    limit: int = 100,
    signal_service: SignalService = Depends(get_signal_service)
):
    """신호 기록을 조회합니다."""
    # 현재 구현에서는 signal_history deque에서 최근 기록 반환
    history = list(signal_service.signal_history)[-limit:] if limit > 0 else list(signal_service.signal_history)
    return create_api_response(
        success=True,
        data=history,
        message="신호 기록 조회 완료"
    )