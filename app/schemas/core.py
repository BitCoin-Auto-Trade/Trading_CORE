"""
프로젝트 전반에서 사용되는 Pydantic 스키마를 정의하는 모듈입니다.

- API 요청/응답 데이터 구조 정의
- 내부 데이터 전송 객체(DTO) 역할
"""

import datetime
from pydantic import BaseModel, Field
from typing import List


# --- Data Schemas ---
class Kline1mData(BaseModel):
    t: int = Field(..., description="Open time")
    T: int = Field(..., description="Close time")
    s: str = Field(..., description="Symbol")
    o: str = Field(..., description="Open price")
    c: str = Field(..., description="Close price")
    h: str = Field(..., description="High price")
    low_price: str = Field(..., alias="l", description="Low price")
    v: str = Field(..., description="Base asset volume")


class OrderBookDepth(BaseModel):
    lastUpdateId: int | None = None
    bids: List[List[str]]
    asks: List[List[str]]
    ts: int | None = None


class TradeData(BaseModel):
    s: str = Field(..., description="Symbol")
    p: str = Field(..., description="Price")
    q: str = Field(..., description="Quantity")
    m: bool = Field(..., description="Is the buyer the market maker?")


class KlineBase(BaseModel):
    timestamp: datetime.datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        from_attributes = True


class FundingRateBase(BaseModel):
    timestamp: datetime.datetime
    symbol: str
    funding_rate: float

    class Config:
        from_attributes = True


class OpenInterestBase(BaseModel):
    timestamp: datetime.datetime
    symbol: str
    open_interest: float

    class Config:
        from_attributes = True


# --- Order Schemas ---
class FuturesAsset(BaseModel):
    asset: str
    wallet_balance: float = Field(..., alias="walletBalance")


class FuturesAccountInfo(BaseModel):
    total_wallet_balance: float = Field(..., alias="totalWalletBalance")
    available_balance: float = Field(..., alias="availableBalance")
    assets: List[FuturesAsset]


class PositionInfo(BaseModel):
    symbol: str
    position_amount: float = Field(..., alias="positionAmt")
    entry_price: float = Field(..., alias="entryPrice")


class OpenOrderInfo(BaseModel):
    symbol: str
    order_id: int = Field(..., alias="orderId")
    side: str
    type: str
    price: float
    orig_qty: float = Field(..., alias="origQty")


class ExchangeSymbolFilter(BaseModel):
    filterType: str
    tickSize: str | None = None
    stepSize: str | None = None


class ExchangeSymbolInfo(BaseModel):
    symbol: str
    status: str
    orderTypes: List[str]
    filters: List[ExchangeSymbolFilter]


class ExchangeInfo(BaseModel):
    symbols: List[ExchangeSymbolInfo]


# --- Signal Schemas ---
class TradingSignal(BaseModel):
    symbol: str
    timestamp: datetime.datetime | None = None
    signal: str
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    position_size: float | None = None
    confidence_score: float | None = None
    message: str | None = None
    metadata: dict | None = None
    
    class Config:
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat(),
        }
        
    def dict(self, **kwargs):
        """dict() 메서드를 오버라이드하여 numpy 타입을 Python 기본 타입으로 변환"""
        result = super().dict(**kwargs)
        return self._convert_numpy_types(result)
    
    @staticmethod
    def _convert_numpy_types(obj):
        """numpy 타입을 Python 기본 타입으로 변환"""
        import numpy as np
        
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif hasattr(np, 'bool_') and isinstance(obj, np.bool_):
            return bool(obj)
        elif str(type(obj)).startswith("<class 'numpy.bool"):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: TradingSignal._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [TradingSignal._convert_numpy_types(item) for item in obj]
        else:
            return obj


# --- Settings Schemas ---
class TradingSettings(BaseModel):
    TIMEFRAME: str = "1m"
    LEVERAGE: int = 10
    RISK_PER_TRADE: float = 0.02
    ACCOUNT_BALANCE: float = 10000.0
    AUTO_TRADING_ENABLED: bool = False  # 기본값을 False로 변경
    ATR_MULTIPLIER: float = 1.5
    TP_RATIO: float = 1.5
    VOLUME_SPIKE_THRESHOLD: float = 2.0
    PRICE_MOMENTUM_THRESHOLD: float = 0.003
    MIN_SIGNAL_INTERVAL_MINUTES: int = 5
    MAX_CONSECUTIVE_LOSSES: int = 3
    ACTIVE_HOURS: List[tuple[int, int]] = [(9, 24), (0, 2)]
