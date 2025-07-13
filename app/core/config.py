import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()


class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    DATABASE_URL: str = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

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

        # Stop-Loss and Take-Profit
        ATR_MULTIPLIER: float = 1.5
        TP_RATIO: float = 1.5

        # Scalping Thresholds
        VOLUME_SPIKE_THRESHOLD: float = 2.0
        PRICE_MOMENTUM_THRESHOLD: float = 0.003

        # Risk Management
        MIN_SIGNAL_INTERVAL_MINUTES: int = 5
        MAX_CONSECUTIVE_LOSSES: int = 3
        ACTIVE_HOURS: list[tuple[int, int]] = [(9, 24), (0, 2)]

    TRADING: TradingSettings = TradingSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
