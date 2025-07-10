import redis
from app.repository.order import OrderRepository

class OrderService:
    def __init__(self, redis_client: redis.Redis):
        self.order_repo = OrderRepository(redis_client)

    def get_kline_1m(self, symbol: str):
        return self.order_repo.get_kline_1m_data(symbol)

    def get_order_book(self, symbol: str):
        return self.order_repo.get_order_book_depth(symbol)

    def get_trades(self, symbol: str, limit: int = 100):
        return self.order_repo.get_recent_trades(symbol, limit)
