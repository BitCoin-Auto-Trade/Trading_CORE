"""
애플리케이션 설정 관리 - 리팩토링된 버전
"""
import os
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()


class DatabaseConfig(BaseSettings):
    """데이터베이스 설정"""
    
    # PostgreSQL
    POSTGRES_USER: str = Field(..., description="PostgreSQL 사용자명")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL 비밀번호")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL 호스트")
    POSTGRES_PORT: str = Field(default="5432", description="PostgreSQL 포트")
    POSTGRES_DB: str = Field(..., description="PostgreSQL 데이터베이스명")
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    @property
    def DATABASE_URL(self) -> str:
        """데이터베이스 연결 URL"""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class RedisConfig(BaseSettings):
    """Redis 설정"""
    
    REDIS_HOST: str = Field(default="localhost", description="Redis 호스트")
    REDIS_PORT: int = Field(default=6379, description="Redis 포트")
    REDIS_DB: int = Field(default=0, description="Redis 데이터베이스 번호")
    REDIS_PASSWORD: str = Field(default="", description="Redis 비밀번호")
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    @property
    def REDIS_URL(self) -> str:
        """Redis 연결 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class BinanceConfig(BaseSettings):
    """Binance API 설정"""
    
    # 메인넷 API
    BINANCE_API_KEY: str = Field(..., description="Binance API 키")
    BINANCE_API_SECRET: str = Field(..., description="Binance API 시크릿")
    
    # 테스트넷 API
    BINANCE_TESTNET_API_KEY: str = Field(..., description="Binance 테스트넷 API 키")
    BINANCE_TESTNET_API_SECRET: str = Field(..., description="Binance 테스트넷 API 시크릿")
    
    # API 엔드포인트
    BINANCE_BASE_URL: str = Field(default="https://fapi.binance.com", description="Binance API 기본 URL")
    BINANCE_TESTNET_URL: str = Field(default="https://testnet.binancefuture.com", description="Binance 테스트넷 URL")
    
    # API 제한
    API_RATE_LIMIT: int = Field(default=1200, description="API 요청 제한 (요청/분)")
    API_TIMEOUT: int = Field(default=30, description="API 타임아웃 (초)")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class TradingConfig(BaseSettings):
    """거래 설정"""
    
    # 거래 심볼
    TRADING_SYMBOLS: str = Field(default="BTCUSDT", description="거래 심볼")
    
    # 거래 전략 설정
    TIMEFRAME: str = Field(default="1m", description="차트 시간프레임")
    LEVERAGE: int = Field(default=10, description="레버리지", ge=1, le=125)
    RISK_PER_TRADE: float = Field(default=0.02, description="거래당 리스크 비율", ge=0.001, le=0.1)
    ACCOUNT_BALANCE: float = Field(default=10000.0, description="계정 잔고", gt=0)
    
    # 자동거래 제어 - 안전을 위해 처음에는 OFF로 설정
    AUTO_TRADING_ENABLED: bool = Field(default=False, description="자동 거래 활성화 여부")
    
    # 손절/익절 설정
    ATR_MULTIPLIER: float = Field(default=1.5, description="ATR 배수", ge=0.5, le=5.0)
    TP_RATIO: float = Field(default=1.5, description="손익비", ge=1.0, le=5.0)
    
    # 스캘핑 임계값
    VOLUME_SPIKE_THRESHOLD: float = Field(default=2.0, description="볼륨 스파이크 임계값")
    PRICE_MOMENTUM_THRESHOLD: float = Field(default=0.003, description="가격 모멘텀 임계값")
    
    # 리스크 관리
    MIN_SIGNAL_INTERVAL_MINUTES: int = Field(default=5, description="최소 신호 간격 (분)")
    MAX_CONSECUTIVE_LOSSES: int = Field(default=3, description="최대 연속 손실 횟수")
    ACTIVE_HOURS: list = Field(default=[(9, 24), (0, 2)], description="활성 거래 시간")
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    @validator('LEVERAGE')
    def validate_leverage(cls, v):
        """레버리지 유효성 검사"""
        if not 1 <= v <= 125:
            raise ValueError('레버리지는 1-125 범위여야 합니다')
        return v


class CacheConfig(BaseSettings):
    """캐시 설정"""
    
    # Redis 캐시 TTL 설정 (초)
    CACHE_TTL_KLINES: int = Field(default=5, description="K-라인 캐시 TTL")
    CACHE_TTL_TRADES: int = Field(default=10, description="거래내역 캐시 TTL")
    CACHE_TTL_POSITIONS: int = Field(default=30, description="포지션 캐시 TTL")
    CACHE_TTL_ACCOUNT: int = Field(default=60, description="계정정보 캐시 TTL")
    
    @property
    def CACHE_CONFIG(self) -> Dict[str, int]:
        """캐시 설정 딕셔너리"""
        return {
            "/api/v1/data/realtime/klines": self.CACHE_TTL_KLINES,
            "/api/v1/data/realtime/trades": self.CACHE_TTL_TRADES,
            "/api/v1/orders/positions": self.CACHE_TTL_POSITIONS,
            "/api/v1/orders/account": self.CACHE_TTL_ACCOUNT,
        }


class LoggingConfig(BaseSettings):
    """로깅 설정"""
    
    LOG_LEVEL: str = Field(default="INFO", description="로그 레벨")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="로그 포맷"
    )
    LOG_FILE: Optional[str] = Field(default="trading_system.log", description="로그 파일명")
    LOG_MAX_SIZE: int = Field(default=10485760, description="로그 파일 최대 크기 (바이트)")  # 10MB
    LOG_BACKUP_COUNT: int = Field(default=5, description="백업 로그 파일 개수")


class NewSettings(BaseSettings):
    """새로운 통합 설정 클래스"""
    
    # 환경 설정
    ENVIRONMENT: str = Field(default="development", description="실행 환경")
    DEBUG: bool = Field(default=False, description="디버그 모드")
    
    # 하위 설정들
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    binance: BinanceConfig = BinanceConfig()
    trading: TradingConfig = TradingConfig()
    cache: CacheConfig = CacheConfig()
    logging: LoggingConfig = LoggingConfig()
    
    class Config:
        """Pydantic 설정"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 추가 필드 허용
    
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_new_settings() -> NewSettings:
    """새로운 설정 인스턴스 반환 (싱글톤)"""
    return NewSettings()


# === 기존 호환성을 위한 코드 ===

class Settings(BaseSettings):
    """기존 호환성을 위한 Settings 클래스"""
    
    # PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str

    # Binance API
    BINANCE_API_KEY: str
    BINANCE_API_SECRET: str
    BINANCE_TESTNET_API_KEY: str
    BINANCE_TESTNET_API_SECRET: str

    # Trading Symbols
    TRADING_SYMBOLS: str = "BTCUSDT"

    # Trading Strategy Settings
    class TradingSettings:
        TIMEFRAME: str = "1m"
        LEVERAGE: int = 10
        RISK_PER_TRADE: float = 0.02
        ACCOUNT_BALANCE: float = 10000.0  # TODO: 실제 잔고 연동 필요

        # Auto Trading Control - 안전을 위해 처음에는 OFF로 설정
        AUTO_TRADING_ENABLED: bool = False  # 자동 거래 활성화 여부

        # Stop-Loss and Take-Profit
        ATR_MULTIPLIER: float = 1.5
        TP_RATIO: float = 1.5

        # Scalping Thresholds
        VOLUME_SPIKE_THRESHOLD: float = 2.0
        PRICE_MOMENTUM_THRESHOLD: float = 0.003

        # Risk Management
        MIN_SIGNAL_INTERVAL_MINUTES: int = 5
        MAX_CONSECUTIVE_LOSSES: int = 3
        ACTIVE_HOURS: list = [(9, 24), (0, 2)]

    TRADING: TradingSettings = TradingSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 기존 인스턴스 유지
settings = Settings()

# 새로운 설정 인스턴스
new_settings = get_new_settings()
