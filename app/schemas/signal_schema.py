import datetime
from pydantic import BaseModel

class TradingSignal(BaseModel):
    symbol: str
    timestamp: datetime.datetime | None = None
    rsi_value: float | None = None
    macd_value: float | None = None
    macd_signal_value: float | None = None
    macd_hist_value: float | None = None
    stop_loss_price: float | None = Field(None, description="계산된 손절 가격")
    take_profit_price: float | None = Field(None, description="계산된 익절 가격")
    signal: str # "BUY", "SELL", "HOLD"
    message: str | None = None
