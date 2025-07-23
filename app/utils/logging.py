"""
구조화된 로깅 시스템을 제공합니다.
"""
import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import json

from app.core.constants import LOG_LEVELS


class StructuredFormatter(logging.Formatter):
    """구조화된 로그 형식을 제공하는 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 추가 필드가 있으면 포함
        if hasattr(record, 'symbol'):
            log_entry["symbol"] = record.symbol
        
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        
        if hasattr(record, 'execution_time'):
            log_entry["execution_time"] = record.execution_time
        
        # 예외 정보 포함
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class TradingLogger:
    """거래 시스템 전용 로거"""
    
    def __init__(self, name: str, level: str = LOG_LEVELS["INFO"]):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """로그 핸들러를 설정합니다."""
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # 파일 핸들러 (JSON 형식)
        file_handler = logging.FileHandler('trading_system.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        
        # 핸들러 추가
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs):
        """정보 로그"""
        self.logger.info(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """디버그 로그"""
        self.logger.debug(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """경고 로그"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """오류 로그"""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """치명적 오류 로그"""
        self.logger.critical(message, extra=kwargs)
    
    def log_trade(self, symbol: str, side: str, price: float, quantity: float, **kwargs):
        """거래 로그"""
        self.info(
            f"거래 실행: {symbol} {side} {quantity} @ {price}",
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            **kwargs
        )
    
    def log_signal(self, symbol: str, signal: str, confidence: float, **kwargs):
        """신호 로그"""
        self.info(
            f"거래 신호: {symbol} {signal} (신뢰도: {confidence:.2f})",
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            **kwargs
        )
    
    def log_position(self, symbol: str, action: str, details: Dict[str, Any], **kwargs):
        """포지션 로그"""
        self.info(
            f"포지션 {action}: {symbol}",
            symbol=symbol,
            action=action,
            details=details,
            **kwargs
        )
    
    def log_performance(self, metric: str, value: float, **kwargs):
        """성능 로그"""
        self.info(
            f"성능 지표: {metric} = {value}",
            metric=metric,
            value=value,
            **kwargs
        )
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, execution_time: float, **kwargs):
        """API 호출 로그"""
        self.info(
            f"API 호출: {method} {endpoint} - {status_code} ({execution_time:.3f}s)",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            execution_time=execution_time,
            **kwargs
        )


# 전역 로거 인스턴스
def get_logger(name: str) -> TradingLogger:
    """로거 인스턴스를 가져옵니다."""
    return TradingLogger(name)


# 기본 로거들
main_logger = get_logger("app.main")
order_logger = get_logger("app.orders")
signal_logger = get_logger("app.signals")
data_logger = get_logger("app.data")
scheduler_logger = get_logger("app.scheduler")

def setup_logging(level: str = LOG_LEVELS["INFO"]) -> None:
    """로깅 시스템을 설정합니다."""
    # 기본 로거 설정
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("trading_core.log")
        ]
    )
    
    # 외부 라이브러리 로거 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    get_logger("app.main").info("로깅 시스템 초기화 완료")


# 편의를 위한 logger 인스턴스 (기존 코드 호환성)
logger = get_logger("app.utils.logging")
