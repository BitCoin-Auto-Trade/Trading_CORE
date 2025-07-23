"""
애플리케이션 전용 예외 클래스들을 정의합니다.
"""
from typing import Optional, Any, Dict


class TradingCoreException(Exception):
    """Trading Core 애플리케이션의 기본 예외 클래스"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class DatabaseException(TradingCoreException):
    """데이터베이스 관련 예외"""
    pass


class RedisException(TradingCoreException):
    """Redis 관련 예외"""
    pass


class BinanceAPIException(TradingCoreException):
    """Binance API 관련 예외"""
    pass


class TradingSignalException(TradingCoreException):
    """거래 신호 관련 예외"""
    pass


class OrderServiceException(TradingCoreException):
    """주문 서비스 관련 예외"""
    pass


class PositionException(TradingCoreException):
    """포지션 관련 예외"""
    pass


class ConfigurationException(TradingCoreException):
    """설정 관련 예외"""
    pass


class ValidationException(TradingCoreException):
    """데이터 검증 실패 예외"""
    pass


class DataNotFoundException(TradingCoreException):
    """데이터를 찾을 수 없는 경우의 예외"""
    pass


class RateLimitException(TradingCoreException):
    """API 호출 제한 관련 예외"""
    pass


class TimeoutException(TradingCoreException):
    """타임아웃 예외"""
    pass


class BinanceAdapterException(TradingCoreException):
    """Binance Adapter 관련 예외"""
    pass


class SignalServiceException(TradingCoreException):
    """Signal Service 관련 예외"""
    pass
