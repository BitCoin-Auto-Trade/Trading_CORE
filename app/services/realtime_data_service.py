"""
실시간 데이터 관련 비즈니스 로직을 처리하는 서비스 모듈입니다.
"""
import redis
from app.repository.redis_repository import RedisRepository
from app.schemas.getdata import Kline1mData, OrderBookDepth, TradeData

class RealtimeDataService:
    """
    실시간 데이터 조회를 위한 서비스 클래스.
    - `redis_repo`: RedisRepository 인스턴스
    """
    def __init__(self, redis_client: redis.Redis):
        self.redis_repo = RedisRepository(redis_client=redis_client)

    def get_kline_1m(self, symbol: str) -> Kline1mData | None:
        """
        최신 1분봉 캔들 데이터를 조회합니다.
        """
        return self.redis_repo.get_kline_1m_data(symbol)

    def get_order_book(self, symbol: str) -> OrderBookDepth | None:
        """
        실시간 오더북 데이터를 조회합니다.
        """
        return self.redis_repo.get_order_book_depth(symbol)

    def get_trades(self, symbol: str, limit: int) -> list[TradeData]:
        """
        최근 체결 내역을 조회합니다.
        """
        return self.redis_repo.get_recent_trades(symbol, limit)
