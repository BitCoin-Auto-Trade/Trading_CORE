"""
Redis 관련 데이터 접근을 처리하는 모듈입니다.
실시간 데이터를 Redis에서 조회합니다.
"""
import json
import redis

class RedisRepository:
    """
    Redis 관련 작업을 위한 리포지토리 클래스.
    - `redis_client`: Redis 클라이언트 객체
    """
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def get_kline_1m_data(self, symbol: str):
        """
        특정 심볼의 최신 1분봉 캔들 데이터를 Redis에서 조회합니다.
        - `symbol`: 조회할 심볼 (예: "BTCUSDT")
        """
        key = f"binance:kline:{symbol.lower()}:1m"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def get_order_book_depth(self, symbol: str):
        """
        특정 심볼의 실시간 오더북 데이터를 Redis에서 조회합니다.
        - `symbol`: 조회할 심볼 (예: "BTCUSDT")
        """
        key = f"binance:depth:{symbol.lower()}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def get_recent_trades(self, symbol: str, limit: int = 100):
        """
        특정 심볼의 최근 체결 내역을 Redis에서 조회합니다.
        - `symbol`: 조회할 심볼 (예: "BTCUSDT")
        - `limit`: 가져올 데이터 개수
        """
        key = f"binance:trades:{symbol.lower()}"
        data = self.redis_client.lrange(key, 0, limit - 1)
        return [json.loads(trade) for trade in data]
