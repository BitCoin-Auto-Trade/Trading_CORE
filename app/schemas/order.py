from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Kline1mData(BaseModel):
    t: int = Field(..., description="Open time")
    T: int = Field(..., description="Close time")
    s: str = Field(..., description="Symbol")
    i: str = Field(..., description="Interval")
    f: int = Field(..., description="First trade ID")
    L: int = Field(..., description="Last trade ID")
    o: str = Field(..., description="Open price")
    c: str = Field(..., description="Close price")
    h: str = Field(..., description="High price")
    l: str = Field(..., description="Low price")
    v: str = Field(..., description="Base asset volume")
    n: int = Field(..., description="Number of trades")
    x: bool = Field(..., description="Is this kline closed?")
    q: str = Field(..., description="Quote asset volume")
    V: str = Field(..., description="Taker buy base asset volume")
    Q: str = Field(..., description="Taker buy quote asset volume")
    B: str = Field(..., description="Ignore")

class OrderBookDepth(BaseModel):
    lastUpdateId: int
    bids: List[List[str]]
    asks: List[List[str]]
    ts: int | None = None # 추가된 필드

class TradeData(BaseModel):
    e: str = Field(..., description="Event type")
    E: int = Field(..., description="Event time")
    s: str = Field(..., description="Symbol")
    a: int = Field(..., description="Aggregate tradeId")
    p: str = Field(..., description="Price")
    q: str = Field(..., description="Quantity")
    f: int = Field(..., description="First tradeId")
    l: int = Field(..., description="Last tradeId")
    T: int = Field(..., description="Trade time")
    m: bool = Field(..., description="Is the buyer the market maker?")
    M: bool = Field(..., description="Ignore")
