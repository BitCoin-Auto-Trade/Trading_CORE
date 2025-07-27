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
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.repository.db_repository import DBRepository
from app.repository.redis_repository import RedisRepository
from app.schemas import core as schemas
from app.core.exceptions import BinanceAdapterException
from app.core.constants import REDIS_KEYS
from app.utils.helpers import timeout, retry_on_failure
from app.utils.logging import logger


class BinanceAdapter:
    """
    Binance 관련 모든 데이터 소스(API, DB, Redis)에 대한 접근을 통합 관리하는 클래스
    """

    def __init__(self, db: Session, redis_client: redis.Redis, testnet: bool = False):
        self.db_repo = DBRepository(db=db)
        self.redis_repo = RedisRepository(redis_client=redis_client)
        self.redis_client = redis_client
        self.client = self._get_binance_client(testnet)

    def _get_binance_client(self, testnet: bool) -> Client:
        """바이낸스 API 클라이언트를 생성합니다."""
        try:
            api_key = (
                settings.BINANCE_TESTNET_API_KEY if testnet else settings.BINANCE_API_KEY
            )
            api_secret = (
                settings.BINANCE_TESTNET_API_SECRET
                if testnet
                else settings.BINANCE_API_SECRET
            )
            
            client = Client(api_key, api_secret, tld="com", testnet=testnet)
            return client
            
        except Exception as e:
            logger.error(f"Binance 클라이언트 생성 실패 (testnet={testnet}): {e}", extra={"error": str(e)})
            raise BinanceAdapterException(f"Binance 클라이언트 생성 실패: {str(e)}")

    def is_api_available(self) -> bool:
        """Binance API 사용 가능 여부를 확인합니다."""
        return self.client is not None

    # --- 과거 데이터 (DB) ---
    def get_klines_data(
        self, symbol: str, interval: str, limit: int
    ) -> list[schemas.KlineBase]:
        """DB에서 캔들 데이터를 조회합니다."""
        try:
            return self.db_repo.get_klines_by_symbol(symbol, limit)
        except Exception as e:
            logger.error(f"캔들 데이터 조회 실패", symbol=symbol, error=str(e))
            raise BinanceAdapterException(f"캔들 데이터 조회 실패: {str(e)}")

    def get_funding_rates_data(
        self, symbol: str, limit: int
    ) -> list[schemas.FundingRateBase]:
        """DB에서 펀딩 수수료 데이터를 조회합니다."""
        try:
            return self.db_repo.get_funding_rates_by_symbol(symbol, limit)
        except Exception as e:
            logger.error(f"펀딩 수수료 데이터 조회 실패", symbol=symbol, error=str(e))
            raise BinanceAdapterException(f"펀딩 수수료 데이터 조회 실패: {str(e)}")

    def get_open_interest_data(
        self, symbol: str, limit: int
    ) -> list[schemas.OpenInterestBase]:
        """DB에서 미결제약정 데이터를 조회합니다."""
        try:
            return self.db_repo.get_open_interest_by_symbol(symbol, limit)
        except Exception as e:
            logger.error(f"미결제약정 데이터 조회 실패", symbol=symbol, error=str(e))
            raise BinanceAdapterException(f"미결제약정 데이터 조회 실패: {str(e)}")

    # --- 실시간 데이터 (Redis) ---
    def get_kline_1m(self, symbol: str) -> schemas.Kline1mData | None:
        """Redis에서 1분봉 데이터를 조회합니다."""
        try:
            return self.redis_repo.get_kline_1m_data(symbol)
        except Exception as e:
            logger.error(f"1분봉 데이터 조회 실패", symbol=symbol, error=str(e))
            return None

    @retry_on_failure(max_retries=3, delay=1)
    def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> dict | None:
        """오더북 데이터를 조회합니다."""
        try:
            return self.redis_repo.get_order_book_depth(symbol, limit)
        except Exception as e:
            logger.error(f"오더북 데이터 조회 실패", symbol=symbol, error=str(e))
            return None

    def get_trades(self, symbol: str, limit: int) -> list[schemas.TradeData]:
        """최근 거래 데이터를 조회합니다."""
        try:
            return self.redis_repo.get_recent_trades(symbol, limit)
        except Exception as e:
            logger.error(f"거래 데이터 조회 실패", symbol=symbol, error=str(e))
            return []

    @timeout(timeout_seconds=10)
    async def get_current_price(self, symbol: str) -> float | None:
        """지정된 심볼의 현재 가격을 API를 통해 직접 조회합니다."""
        # API 사용 불가능한 경우 Redis에서만 조회
        if not self.is_api_available():
            cached_price = self.redis_client.get(f"{REDIS_KEYS['PRICE_PREFIX']}{symbol}")
            if cached_price:
                return float(cached_price)
            logger.warning(f"API 비활성화 상태, 캐시된 가격도 없음: {symbol}")
            return None
            
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            
            # Redis에 가격 캐시 저장
            self.redis_client.setex(
                f"{REDIS_KEYS['PRICE_PREFIX']}{symbol}", 
                60,  # 1분 TTL
                str(price)
            )
            
            return price
        except Exception as e:
            logger.error(f"현재 가격 조회 실패", symbol=symbol, error=str(e))
            # API 실패 시 캐시된 값 반환 시도
            cached_price = self.redis_client.get(f"{REDIS_KEYS['PRICE_PREFIX']}{symbol}")
            if cached_price:
                logger.info(f"API 실패로 캐시된 가격 사용: {symbol}")
                return float(cached_price)
            return None

    async def get_latest_price(self, symbol: str) -> float:
        """최신 가격을 조회합니다 (Redis -> API 순서)."""
        try:
            # 먼저 Redis에서 캐시된 가격 조회
            cached_price = self.redis_client.get(f"{REDIS_KEYS['PRICE_PREFIX']}{symbol}")
            if cached_price:
                return float(cached_price)
            
            # 캐시된 가격이 없으면 API 호출
            price = await self.get_current_price(symbol)
            if price:
                return price
            
            raise BinanceAdapterException(f"가격 조회 실패: {symbol}")
            
        except Exception as e:
            logger.error(f"최신 가격 조회 실패", symbol=symbol, error=str(e))
            raise BinanceAdapterException(f"최신 가격 조회 실패: {str(e)}")

    @timeout(timeout_seconds=10)
    def get_account_info(self) -> Dict[str, Any]:
        """계좌 정보를 조회합니다."""
        try:
            return self.client.get_account()
        except Exception as e:
            logger.error(f"계좌 정보 조회 실패", error=str(e))
            raise BinanceAdapterException(f"계좌 정보 조회 실패: {str(e)}")

    @timeout(timeout_seconds=30)
    def place_order(self, symbol: str, side: str, quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
        """주문을 생성합니다."""
        try:
            order_params = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET" if price is None else "LIMIT",
                "quantity": quantity,
            }
            
            if price is not None:
                order_params["price"] = price
                order_params["timeInForce"] = "GTC"
            
            result = self.client.create_order(**order_params)
            logger.info(f"주문 생성 완료", symbol=symbol, side=side, quantity=quantity, price=price)
            return result
            
        except Exception as e:
            logger.error(f"주문 생성 실패", symbol=symbol, side=side, error=str(e))
            raise BinanceAdapterException(f"주문 생성 실패: {str(e)}")

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """미체결 주문을 조회합니다."""
        try:
            if symbol:
                return self.client.get_open_orders(symbol=symbol)
            else:
                return self.client.get_open_orders()
        except Exception as e:
            logger.error(f"미체결 주문 조회 실패", symbol=symbol, error=str(e))
            raise BinanceAdapterException(f"미체결 주문 조회 실패: {str(e)}")

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """주문을 취소합니다."""
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"주문 취소 완료", symbol=symbol, order_id=order_id)
            return result
        except Exception as e:
            logger.error(f"주문 취소 실패", symbol=symbol, order_id=order_id, error=str(e))
            raise BinanceAdapterException(f"주문 취소 실패: {str(e)}")

    

    # --- 계좌 및 주문 (Binance API) ---
    def get_position_info(self) -> list[schemas.PositionInfo]:
        positions = self.client.futures_position_information()
        active_positions = [p for p in positions if float(p["positionAmt"]) != 0]
        return [schemas.PositionInfo.model_validate(p) for p in active_positions]

    async def close_position(self, symbol: str, position_side: str = None) -> Dict[str, Any]:
        """포지션 전체 종료"""
        try:
            # 현재 포지션 정보 조회
            position_info = self.client.futures_position_information(symbol=symbol)
            
            for position in position_info:
                position_amt = float(position['positionAmt'])
                
                # 포지션이 있는 경우에만 종료
                if position_amt != 0:
                    # 롱 포지션이면 SELL, 숏 포지션이면 BUY로 종료
                    side = 'SELL' if position_amt > 0 else 'BUY'
                    quantity = abs(position_amt)
                    
                    # 시장가로 포지션 종료
                    result = self.client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type='MARKET',
                        quantity=quantity,
                        reduceOnly=True  # 포지션 감소 전용
                    )
                    
                    logger.info(
                        f"포지션 종료 주문 성공",
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        order_id=result.get('orderId')
                    )
                    
                    return result
            
            # 종료할 포지션이 없는 경우
            logger.warning(f"종료할 포지션이 없습니다: {symbol}")
            return {"message": "No position to close", "symbol": symbol}
            
        except Exception as e:
            logger.error(f"포지션 종료 실패", symbol=symbol, error=str(e))
            raise BinanceAdapterException(f"포지션 종료 실패: {str(e)}")

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
