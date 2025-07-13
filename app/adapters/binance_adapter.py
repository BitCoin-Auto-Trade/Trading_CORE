"""
외부 서비스인 Binance와의 모든 통신을 담당하는 어댑터 모듈입니다.

- Binance API 클라이언트 생성 및 관리
- 실시간 데이터(Redis) 조회
- 과거 데이터(DB) 조회
- 계좌 정보, 주문 등 API 직접 호출
"""

import redis
from sqlalchemy.orm import Session
from binance.client import Client
from app.core.config import settings
from app.repository.db_repository import DBRepository
from app.repository.redis_repository import RedisRepository
from app.schemas import core as schemas


class BinanceAdapter:
    """
    Binance 관련 모든 데이터 소스(API, DB, Redis)에 대한 접근을 통합 관리하는 클래스
    """

    def __init__(self, db: Session, redis_client: redis.Redis, testnet: bool = False):
        self.db_repo = DBRepository(db=db)
        self.redis_repo = RedisRepository(redis_client=redis_client)
        self.client = self._get_binance_client(testnet)

    def _get_binance_client(self, testnet: bool) -> Client:
        """바이낸스 API 클라이언트를 생성합니다."""
        api_key = (
            settings.BINANCE_TESTNET_API_KEY if testnet else settings.BINANCE_API_KEY
        )
        api_secret = (
            settings.BINANCE_TESTNET_API_SECRET
            if testnet
            else settings.BINANCE_API_SECRET
        )
        return Client(api_key, api_secret, tld="com", testnet=testnet)

    # --- 과거 데이터 (DB) ---
    def get_klines_data(
        self, symbol: str, interval: str, limit: int
    ) -> list[schemas.KlineBase]:
        return self.db_repo.get_klines_by_symbol(symbol, limit)

    def get_funding_rates_data(
        self, symbol: str, limit: int
    ) -> list[schemas.FundingRateBase]:
        return self.db_repo.get_funding_rates_by_symbol(symbol, limit)

    def get_open_interest_data(
        self, symbol: str, limit: int
    ) -> list[schemas.OpenInterestBase]:
        return self.db_repo.get_open_interest_by_symbol(symbol, limit)

    # --- 실시간 데이터 (Redis) ---
    def get_kline_1m(self, symbol: str) -> schemas.Kline1mData | None:
        return self.redis_repo.get_kline_1m_data(symbol)

    def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> schemas.OrderBookDepth | None:
        return self.redis_repo.get_order_book_depth(symbol, limit)

    def get_trades(self, symbol: str, limit: int) -> list[schemas.TradeData]:
        return self.redis_repo.get_recent_trades(symbol, limit)

    async def get_current_price(self, symbol: str) -> float | None:
        """지정된 심볼의 현재 가격을 API를 통해 직접 조회합니다."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            # 로깅 추가를 고려해볼 수 있습니다.
            print(f"Error fetching price for {symbol}: {e}")
            return None

    # --- 계좌 및 주문 (Binance API) ---
    def get_position_info(self) -> list[schemas.PositionInfo]:
        positions = self.client.futures_position_information()
        active_positions = [p for p in positions if float(p["positionAmt"]) != 0]
        return [schemas.PositionInfo.model_validate(p) for p in active_positions]

    def get_futures_account_balance(self) -> schemas.FuturesAccountInfo:
        account_info = self.client.futures_account()
        filtered_assets = [
            asset
            for asset in account_info["assets"]
            if float(asset["walletBalance"]) > 0
        ]
        account_info["assets"] = filtered_assets
        return schemas.FuturesAccountInfo.model_validate(account_info)

    def get_open_orders(self, symbol: str | None = None) -> list[schemas.OpenOrderInfo]:
        params = {"symbol": symbol} if symbol else {}
        open_orders = self.client.get_open_orders(**params)
        return [schemas.OpenOrderInfo.model_validate(o) for o in open_orders]

    def get_exchange_info(self) -> schemas.ExchangeInfo:
        exchange_info = self.client.get_exchange_info()
        futures_symbols = [
            s
            for s in exchange_info["symbols"]
            if s.get("contractType") == "PERPETUAL" and s.get("status") == "TRADING"
        ]
        return schemas.ExchangeInfo(symbols=futures_symbols)
