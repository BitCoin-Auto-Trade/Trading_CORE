"""
주문 및 계좌 관련 API의 응답 모델을 정의하는 모듈입니다.
"""
from pydantic import BaseModel, Field
from typing import List, Any

# --- /account/futures ---
class FuturesAsset(BaseModel):
    asset: str = Field(..., description="자산 이름 (e.g., USDT)")
    wallet_balance: float = Field(..., alias="walletBalance", description="지갑 잔고")
    unrealized_profit: float = Field(..., alias="unrealizedProfit", description="미실현 손익")
    margin_balance: float = Field(..., alias="marginBalance", description="마진 잔고")

class FuturesAccountInfo(BaseModel):
    total_wallet_balance: float = Field(..., alias="totalWalletBalance", description="총 지갑 잔고")
    total_unrealized_profit: float = Field(..., alias="totalUnrealizedProfit", description="총 미실현 손익")
    total_margin_balance: float = Field(..., alias="totalMarginBalance", description="총 마진 잔고")
    available_balance: float = Field(..., alias="availableBalance", description="출금 가능 잔고")
    assets: List[FuturesAsset] = Field(..., description="자산별 상세 정보 (잔고 > 0)")

# --- /position ---
class PositionInfo(BaseModel):
    symbol: str = Field(..., description="심볼 이름 (e.g., BTCUSDT)")
    position_amount: float = Field(..., alias="positionAmt", description="포지션 수량 (롱: 양수, 숏: 음수)")
    entry_price: float = Field(..., alias="entryPrice", description="진입 가격")
    mark_price: float = Field(..., alias="markPrice", description="시장 평균 가격")
    unrealized_profit: float = Field(..., alias="unRealizedProfit", description="미실현 손익")
    leverage: int = Field(..., description="레버리지")
    margin_type: str = Field(..., alias="marginType", description="마진 타입 (cross, isolated)")

# --- /orders/open ---
class OpenOrderInfo(BaseModel):
    symbol: str = Field(..., description="심볼 이름")
    order_id: int = Field(..., alias="orderId", description="주문 ID")
    side: str = Field(..., description="주문 사이드 (BUY, SELL)")
    type: str = Field(..., description="주문 유형 (LIMIT, MARKET, etc.)")
    price: float = Field(..., description="주문 가격")
    orig_qty: float = Field(..., alias="origQty", description="주문 수량")
    executed_qty: float = Field(..., alias="executedQty", description="체결된 수량")
    time: int = Field(..., description="주문 시간 (timestamp)")

# --- /exchange-info ---
class ExchangeSymbolFilter(BaseModel):
    filterType: str
    minPrice: str | None = None
    maxPrice: str | None = None
    tickSize: str | None = None
    minQty: str | None = None
    maxQty: str | None = None
    stepSize: str | None = None
    minNotional: str | None = None

class ExchangeSymbolInfo(BaseModel):
    symbol: str
    status: str
    orderTypes: List[str]
    filters: List[ExchangeSymbolFilter]

class ExchangeInfo(BaseModel):
    symbols: List[ExchangeSymbolInfo]
