"""
애플리케이션 전체에서 사용하는 상수 정의

모든 상수는 의미가 명확하고 일관된 네이밍 컨벤션을 따른다.
- 카테고리별로 그룹화하여 관리 
- 매직 넘버를 상수로 치환하여 가독성 향상
- 한국어 주석으로 의미 명확화
"""
from typing import Final

# Redis 키 패턴 상수
REDIS_KEY_PATTERNS: Final = {
    # 포지션 관련
    "POSITION_PREFIX": "position:",
    "POSITION_SUMMARY": "position:summary",
    
    # 거래 신호 관련  
    "TRADING_SIGNAL_PREFIX": "trading_signal:",
    "SIGNAL_CACHE_PREFIX": "signal_cache:",
    
    # 가격 데이터 관련
    "PRICE_DATA_PREFIX": "price:",
    "KLINE_1M_PREFIX": "kline_1m:",
    "ORDER_BOOK_PREFIX": "orderbook:",
    "TRADE_DATA_PREFIX": "trade:",
    
    # 성과 및 설정
    "PERFORMANCE_KEY": "performance",
    "TRADING_SETTINGS_KEY": "trading_settings",
    "AUTO_TRADING_STATUS_KEY": "auto_trading_enabled",
    
    # 캐시 관련
    "CACHE_PREFIX": "cache:",
    "RATE_LIMIT_PREFIX": "rate_limit:",
}

# 거래 상수 정의
class TradingConstants:
    """거래 관련 상수들을 클래스로 그룹화"""
    
    # 포지션 방향
    class PositionSide:
        LONG = "LONG"
        SHORT = "SHORT"
    
    # 거래 신호 타입
    class SignalType:
        BUY = "BUY"
        SELL = "SELL" 
        HOLD = "HOLD"
    
    # 포지션 상태
    class PositionStatus:
        ACTIVE = "ACTIVE"
        CLOSED = "CLOSED"
        PENDING = "PENDING"
    
    # 포지션 종료 사유
    class CloseReason:
        STOP_LOSS_HIT = "STOP_LOSS_HIT"
        TAKE_PROFIT_HIT = "TAKE_PROFIT_HIT" 
        MANUAL_CLOSE = "MANUAL_CLOSE"
        EMERGENCY_STOP = "EMERGENCY_STOP"
        TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
        VOLATILITY_EXIT = "VOLATILITY_EXIT"
        TRAILING_STOP_HIT = "TRAILING_STOP_HIT"
    
    # 거래 결과
    class TradeResult:
        PROFIT = "PROFIT"
        LOSS = "LOSS"
        BREAKEVEN = "BREAKEVEN"
    
    # 시장 추세
    class MarketTrend:
        STRONG_BULLISH = "STRONG_UP"
        WEAK_BULLISH = "WEAK_UP" 
        NEUTRAL = "NEUTRAL"
        WEAK_BEARISH = "WEAK_DOWN"
        STRONG_BEARISH = "STRONG_DOWN"

# 기본 설정값 상수
class DefaultSettings:
    """기본 거래 설정값들을 클래스로 그룹화"""
    
    # 포지션 관리
    DEFAULT_POSITION_SIZE = 1000
    MAX_POSITIONS = 5
    MAX_POSITION_HOLD_HOURS = 4
    
    # 리스크 관리
    STOP_LOSS_RATIO = 0.02  # 2% 손절
    RISK_PER_TRADE = 0.02   # 거래당 리스크 2%
    MAX_CONSECUTIVE_LOSSES = 3
    LEVERAGE = 10
    
    # 기술적 지표 설정
    ATR_MULTIPLIER = 1.5
    TRAILING_STOP_ACTIVATION_RATIO = 1.5
    TRAILING_STOP_ATR_MULTIPLIER = 2.0
    
    # 신호 생성 설정
    MIN_SIGNAL_INTERVAL_MINUTES = 2
    SIGNAL_COOLDOWN_MINUTES = 5
    
    # 시장 분석 임계값
    VOLUME_SPIKE_THRESHOLD = 2.0
    VOLATILITY_HIGH_THRESHOLD = 0.05
    VOLATILITY_EXIT_THRESHOLD = 0.03
    MACD_HISTOGRAM_THRESHOLD = 0.0001
    
    # 시스템 설정
    MONITORING_INTERVAL_SECONDS = 5
    ACCOUNT_BALANCE = 10000.0

# API 응답 상태 코드
class ApiResponseStatus:
    """API 응답 상태를 나타내는 상수"""
    
    SUCCESS = "success"
    ERROR = "error" 
    WARNING = "warning"
    PARTIAL_SUCCESS = "partial_success"

# 로깅 레벨 상수
class LogLevel:
    """로깅 레벨 상수 정의"""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# 데이터베이스 관련 상수
class DatabaseConfig:
    """데이터베이스 설정 관련 상수"""
    
    # 쿼리 제한
    DEFAULT_QUERY_LIMIT = 100
    MAX_QUERY_LIMIT = 1000
    MIN_QUERY_LIMIT = 1
    
    # 테이블명
    KLINE_TABLE_NAME = "klines_1m"
    FUNDING_RATE_TABLE_NAME = "funding_rates"
    OPEN_INTEREST_TABLE_NAME = "open_interest"
    
    # 연결 설정
    CONNECTION_TIMEOUT_SECONDS = 30
    QUERY_TIMEOUT_SECONDS = 10

# 외부 API 설정 상수
class ExternalApiConfig:
    """외부 API 연결 설정 상수"""
    
    class Binance:
        """바이낸스 API 설정"""
        TIMEOUT_SECONDS = 30
        RETRY_COUNT = 3
        RETRY_DELAY_SECONDS = 1
        RATE_LIMIT_PER_MINUTE = 1200
        
    class Redis:
        """Redis 연결 설정"""
        TIMEOUT_SECONDS = 5
        RETRY_ON_TIMEOUT = True
        HEALTH_CHECK_INTERVAL_SECONDS = 30
        MAX_CONNECTIONS = 100

# 하위 호환성을 위한 기존 상수들 (점진적 마이그레이션용)
REDIS_KEYS: Final = {
    # 기존 키들 (하위 호환성)
    "POSITION": "position:",
    "POSITION_PREFIX": "position:",
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
    
    # 새로운 키들  
    **REDIS_KEY_PATTERNS
}  # 기존 코드 호환성
TRADING: Final = {
    "SIDES": {
        "LONG": TradingConstants.PositionSide.LONG,
        "SHORT": TradingConstants.PositionSide.SHORT,
    },
    "SIGNALS": {
        "BUY": TradingConstants.SignalType.BUY,
        "SELL": TradingConstants.SignalType.SELL,
        "HOLD": TradingConstants.SignalType.HOLD,
    },
    "POSITION_STATUSES": {
        "ACTIVE": TradingConstants.PositionStatus.ACTIVE,
        "CLOSED": TradingConstants.PositionStatus.CLOSED,
    },
    "CLOSE_REASONS": {
        "STOP_LOSS_HIT": TradingConstants.CloseReason.STOP_LOSS_HIT,
        "TAKE_PROFIT_HIT": TradingConstants.CloseReason.TAKE_PROFIT_HIT,
        "MANUAL_CLOSE": TradingConstants.CloseReason.MANUAL_CLOSE,
        "EMERGENCY_STOP": TradingConstants.CloseReason.EMERGENCY_STOP,
        "TIME_LIMIT_EXCEEDED": TradingConstants.CloseReason.TIME_LIMIT_EXCEEDED,
        "VOLATILITY_EXIT": TradingConstants.CloseReason.VOLATILITY_EXIT,
    },
    "RESULTS": {
        "PROFIT": TradingConstants.TradeResult.PROFIT,
        "LOSS": TradingConstants.TradeResult.LOSS,
    },
    "TRENDS": {
        "STRONG_UP": TradingConstants.MarketTrend.STRONG_BULLISH,
        "WEAK_UP": TradingConstants.MarketTrend.WEAK_BULLISH,
        "NEUTRAL": TradingConstants.MarketTrend.NEUTRAL,
        "WEAK_DOWN": TradingConstants.MarketTrend.WEAK_BEARISH,
        "STRONG_DOWN": TradingConstants.MarketTrend.STRONG_BEARISH,
    },
}

DEFAULTS: Final = {
    "POSITION_SIZE": DefaultSettings.DEFAULT_POSITION_SIZE,
    "STOP_LOSS_RATIO": DefaultSettings.STOP_LOSS_RATIO,
    "MAX_POSITIONS": DefaultSettings.MAX_POSITIONS,
    "MONITORING_INTERVAL": DefaultSettings.MONITORING_INTERVAL_SECONDS,
    "TRAILING_STOP_ACTIVATION_RATIO": DefaultSettings.TRAILING_STOP_ACTIVATION_RATIO,
    "TRAILING_STOP_ATR_MULTIPLIER": DefaultSettings.TRAILING_STOP_ATR_MULTIPLIER,
    "MAX_POSITION_HOLD_HOURS": DefaultSettings.MAX_POSITION_HOLD_HOURS,
    "VOLATILITY_EXIT_THRESHOLD": DefaultSettings.VOLATILITY_EXIT_THRESHOLD,
    "VOLUME_SPIKE_THRESHOLD": DefaultSettings.VOLUME_SPIKE_THRESHOLD,
    "VOLATILITY_HIGH_THRESHOLD": DefaultSettings.VOLATILITY_HIGH_THRESHOLD,
    "MACD_HIST_THRESHOLD": DefaultSettings.MACD_HISTOGRAM_THRESHOLD,
    "MIN_SIGNAL_INTERVAL_MINUTES": DefaultSettings.MIN_SIGNAL_INTERVAL_MINUTES,
    "MAX_CONSECUTIVE_LOSSES": DefaultSettings.MAX_CONSECUTIVE_LOSSES,
    "LEVERAGE": DefaultSettings.LEVERAGE,
    "RISK_PER_TRADE": DefaultSettings.RISK_PER_TRADE,
    "ACCOUNT_BALANCE": DefaultSettings.ACCOUNT_BALANCE,
    "ATR_MULTIPLIER": DefaultSettings.ATR_MULTIPLIER,
    "SIGNAL_COOLDOWN_MINUTES": DefaultSettings.SIGNAL_COOLDOWN_MINUTES,
}

API_STATUS: Final = {
    "SUCCESS": ApiResponseStatus.SUCCESS,
    "ERROR": ApiResponseStatus.ERROR,
    "WARNING": ApiResponseStatus.WARNING,
}

LOG_LEVELS: Final = {
    "DEBUG": LogLevel.DEBUG,
    "INFO": LogLevel.INFO,
    "WARNING": LogLevel.WARNING,
    "ERROR": LogLevel.ERROR,
    "CRITICAL": LogLevel.CRITICAL,
}

DATABASE: Final = {
    "DEFAULT_LIMIT": DatabaseConfig.DEFAULT_QUERY_LIMIT,
    "MAX_LIMIT": DatabaseConfig.MAX_QUERY_LIMIT,
    "KLINE_TABLE": DatabaseConfig.KLINE_TABLE_NAME,
    "FUNDING_RATE_TABLE": DatabaseConfig.FUNDING_RATE_TABLE_NAME,
    "OPEN_INTEREST_TABLE": DatabaseConfig.OPEN_INTEREST_TABLE_NAME,
}

EXTERNAL_API: Final = {
    "BINANCE": {
        "TIMEOUT": ExternalApiConfig.Binance.TIMEOUT_SECONDS,
        "RETRY_COUNT": ExternalApiConfig.Binance.RETRY_COUNT,
        "RETRY_DELAY": ExternalApiConfig.Binance.RETRY_DELAY_SECONDS,
    },
    "REDIS": {
        "TIMEOUT": ExternalApiConfig.Redis.TIMEOUT_SECONDS,
        "RETRY_ON_TIMEOUT": ExternalApiConfig.Redis.RETRY_ON_TIMEOUT,
        "HEALTH_CHECK_INTERVAL": ExternalApiConfig.Redis.HEALTH_CHECK_INTERVAL_SECONDS,
    },
}
