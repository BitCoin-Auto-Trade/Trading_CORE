"""
애플리케이션 전체에서 사용하는 상수들을 정의합니다.
"""
from typing import Final

# Redis 키 프리픽스
REDIS_KEYS: Final = {
    "POSITION": "position:",
    "TRADING_SIGNAL": "trading_signal:",
    "PRICE_PREFIX": "price:",
    "PERFORMANCE": "performance",
    "KLINE_1M_PREFIX": "kline_1m:",
    "ORDER_BOOK_PREFIX": "orderbook:",
    "TRADE_PREFIX": "trade:",
    "CACHE_PREFIX": "cache:",
    "AUTO_TRADING_ENABLED": "auto_trading_enabled",
    "RISK_PER_TRADE": "risk_per_trade",
    "MAX_POSITIONS": "max_positions",
    "TRADING_SYMBOLS": "trading_symbols",
    "TRADING_SETTINGS": "trading_settings",
}

# 거래 관련 상수
TRADING: Final = {
    "SIDES": {
        "LONG": "LONG",
        "SHORT": "SHORT",
    },
    "SIGNALS": {
        "BUY": "BUY",
        "SELL": "SELL",
        "HOLD": "HOLD",
    },
    "POSITION_STATUSES": {
        "ACTIVE": "ACTIVE",
        "CLOSED": "CLOSED",
    },
    "CLOSE_REASONS": {
        "STOP_LOSS_HIT": "STOP_LOSS_HIT",
        "TAKE_PROFIT_HIT": "TAKE_PROFIT_HIT",
        "MANUAL_CLOSE": "MANUAL_CLOSE",
        "EMERGENCY_STOP": "EMERGENCY_STOP",
        "TIME_LIMIT_EXCEEDED": "TIME_LIMIT_EXCEEDED",
        "VOLATILITY_EXIT": "VOLATILITY_EXIT",
    },
    "RESULTS": {
        "PROFIT": "PROFIT",
        "LOSS": "LOSS",
    },
    "TRENDS": {
        "STRONG_UP": "STRONG_UP",
        "WEAK_UP": "WEAK_UP",
        "NEUTRAL": "NEUTRAL",
        "WEAK_DOWN": "WEAK_DOWN",
        "STRONG_DOWN": "STRONG_DOWN",
    },
}

# 기본값
DEFAULTS: Final = {
    "POSITION_SIZE": 1000,
    "STOP_LOSS_RATIO": 0.02,  # 2% 손절
    "MAX_POSITIONS": 5,
    "MONITORING_INTERVAL": 5,  # 초
    "TRAILING_STOP_ACTIVATION_RATIO": 1.5,
    "TRAILING_STOP_ATR_MULTIPLIER": 2.0,
    "MAX_POSITION_HOLD_HOURS": 4,
    "VOLATILITY_EXIT_THRESHOLD": 0.03,
    "VOLUME_SPIKE_THRESHOLD": 2.0,
    "VOLATILITY_HIGH_THRESHOLD": 0.05,
    "MACD_HIST_THRESHOLD": 0.0001,
    "MIN_SIGNAL_INTERVAL_MINUTES": 2,
    "MAX_CONSECUTIVE_LOSSES": 3,
    "LEVERAGE": 10,
    "RISK_PER_TRADE": 0.02,
    "ACCOUNT_BALANCE": 10000,
    "ATR_MULTIPLIER": 1.5,
    "SIGNAL_COOLDOWN_MINUTES": 5,
}

# API 응답 상태
API_STATUS: Final = {
    "SUCCESS": "success",
    "ERROR": "error",
    "WARNING": "warning",
}

# 로그 레벨
LOG_LEVELS: Final = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "CRITICAL": "CRITICAL",
}

# 데이터베이스 관련
DATABASE: Final = {
    "DEFAULT_LIMIT": 100,
    "MAX_LIMIT": 1000,
    "KLINE_TABLE": "klines_1m",
    "FUNDING_RATE_TABLE": "funding_rates",
    "OPEN_INTEREST_TABLE": "open_interest",
}

# 외부 API 관련
EXTERNAL_API: Final = {
    "BINANCE": {
        "TIMEOUT": 30,
        "RETRY_COUNT": 3,
        "RETRY_DELAY": 1,
    },
    "REDIS": {
        "TIMEOUT": 5,
        "RETRY_ON_TIMEOUT": True,
        "HEALTH_CHECK_INTERVAL": 30,
    },
}
