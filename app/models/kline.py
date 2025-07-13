from sqlalchemy import Column, DateTime, String, Float
from . import Base

class Kline_1m(Base):
    __tablename__ = 'klines_1m'

    timestamp = Column(DateTime, primary_key=True)
    symbol = Column(String, primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    ema_20 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    atr: float | None = Column(Float, nullable=True)
