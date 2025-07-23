"""
구조화된 로깅 시스템을 제공합니다.
"""
import logging
import sys
from typing import Dict, Any
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
        extra_fields = ['symbol', 'user_id', 'request_id', 'execution_time', 'details', 'action', 'metric', 'value', 'endpoint', 'method', 'status_code', 'error']
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        # 예외 정보 포함
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class TradingLogger(logging.Logger):
    """거래 시스템 전용 로거"""
    
    def log_trade(self, symbol: str, side: str, price: float, quantity: float, **kwargs):
        """거래 로그"""
        self.info(
            f"거래 실행: {symbol} {side} {quantity} @ {price}",
            extra={"symbol": symbol, "side": side, "price": price, "quantity": quantity, **kwargs}
        )
    
    def log_signal(self, symbol: str, signal: str, confidence: float, **kwargs):
        """신호 로그"""
        self.info(
            f"거래 신호: {symbol} {signal} (신뢰도: {confidence:.2f})",
            extra={"symbol": symbol, "signal": signal, "confidence": confidence, **kwargs}
        )
    
    def log_position(self, symbol: str, action: str, details: Dict[str, Any], **kwargs):
        """포지션 로그"""
        self.info(
            f"포지션 {action}: {symbol}",
            extra={"symbol": symbol, "action": action, "details": details, **kwargs}
        )
    
    def log_performance(self, metric: str, value: float, **kwargs):
        """성능 로그"""
        self.info(
            f"성능 지표: {metric} = {value}",
            extra={"metric": metric, "value": value, **kwargs}
        )
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, execution_time: float, **kwargs):
        """API 호출 로그"""
        self.info(
            f"API 호출: {method} {endpoint} - {status_code} ({execution_time:.3f}s)",
            extra={"endpoint": endpoint, "method": method, "status_code": status_code, "execution_time": execution_time, **kwargs}
        )

# 전역 로거 인스턴스
logging.setLoggerClass(TradingLogger)

def get_logger(name: str) -> TradingLogger:
    """로거 인스턴스를 가져옵니다."""
    return logging.getLogger(name)

def setup_logging(level: str = LOG_LEVELS["INFO"]) -> None:
    """로깅 시스템을 설정합니다."""
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    
    # 핸들러 중복 추가 방지
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (JSON 형식)
    file_handler = logging.FileHandler('trading_system.log')
    file_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(file_handler)
    
    # 외부 라이브러리 로거 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    
    get_logger("app.main").info("로깅 시스템 초기화 완료")

# 편의를 위한 logger 인스턴스 (기존 코드 호환성)
logger = get_logger("app.utils.logging")