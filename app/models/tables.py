"""
데이터베이스 테이블 모델을 정의하는 모듈입니다.

- SQLAlchemy의 Declarative Base를 사용하여 모든 DB 모델을 관리합니다.
"""

from sqlalchemy import Column, DateTime, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Kline_1m(Base):
    __tablename__ = "klines_1m"
    timestamp = Column(DateTime, primary_key=True)
    symbol = Column(String, primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    ema_20 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    atr = Column(Float, nullable=True)
    adx = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    bb_upper = Column(Float, nullable=True)
    bb_middle = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    stoch_k = Column(Float, nullable=True)
    stoch_d = Column(Float, nullable=True)
    volume_sma_20 = Column(Float, nullable=True)     
    volume_ratio = Column(Float, nullable=True)       
    price_momentum_5m = Column(Float, nullable=True)
    volatility_20d = Column(Float, nullable=True) 


class FundingRate(Base):
    __tablename__ = "funding_rates"
    timestamp = Column(DateTime, primary_key=True)
    symbol = Column(String, primary_key=True)
    funding_rate = Column(Float)


class OpenInterest(Base):
    __tablename__ = "open_interest"
    timestamp = Column(DateTime, primary_key=True)
    symbol = Column(String, primary_key=True)
    open_interest = Column(Float)
