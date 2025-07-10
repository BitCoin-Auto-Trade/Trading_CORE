import datetime
from pydantic import BaseModel

# --- Pydantic 모델 정의 ---
class KlineBase(BaseModel):
    timestamp: datetime.datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    ema_20: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None

    class Config:
        orm_mode = True

class FundingRateBase(BaseModel):
    timestamp: datetime.datetime
    symbol: str
    funding_rate: float

    class Config:
        orm_mode = True

class OpenInterestBase(BaseModel):
    timestamp: datetime.datetime
    symbol: str
    open_interest: float

    class Config:
        orm_mode = True

class TradingSignal(BaseModel):
    symbol: str
    timestamp: datetime.datetime | None = None
    rsi_value: float | None = None
    macd_value: float | None = None
    macd_signal_value: float | None = None
    macd_hist_value: float | None = None
    signal: str # "BUY", "SELL", "HOLD"
    message: str | None = None
