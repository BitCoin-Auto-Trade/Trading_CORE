import json
import redis

class OrderRepository:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def get_kline_1m_data(self, symbol: str):
        key = f"binance:kline:{symbol.lower()}:1m"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def get_order_book_depth(self, symbol: str):
        key = f"binance:depth:{symbol.lower()}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def get_recent_trades(self, symbol: str, limit: int = 100):
        key = f"binance:trades:{symbol.lower()}"
        data = self.redis_client.lrange(key, 0, limit - 1)
        return [json.loads(trade) for trade in data]
