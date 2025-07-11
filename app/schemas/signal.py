import datetime
from pydantic import BaseModel

class TradingSignal(BaseModel):
    symbol: str
    timestamp: datetime.datetime | None = None
    rsi_value: float | None = None
    macd_value: float | None = None
    macd_signal_value: float | None = None
    macd_hist_value: float | None = None
    signal: str # "BUY", "SELL", "HOLD"
    message: str | None = None
