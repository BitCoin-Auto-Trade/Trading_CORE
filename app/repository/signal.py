import json
import redis
from sqlalchemy.orm import Session
from app.models.kline import Kline_1m
from app.models.funding_rate import FundingRate
from app.models.open_interest import OpenInterest

class SignalRepository:
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis_client = redis_client

    def get_klines_by_symbol(self, symbol: str, limit: int = 100):
        """
        특정 심볼의 kline 데이터를 Redis에서 가져옵니다.
        """
        key = f"binance:kline:{symbol.lower()}:1m"
        data = self.redis_client.get(key)
        if data:
            # Redis에서 가져온 데이터는 JSON 문자열이므로 파싱해야 합니다.
            # 실제 Kline_1m 모델 객체로 변환하는 로직이 필요합니다.
            # 여기서는 간단히 JSON 파싱 후 딕셔너리 리스트로 반환합니다.
            # TODO: 실제 Kline_1m 모델 객체로 변환하는 로직 추가
            return [json.loads(data)] # 현재는 1개만 가져오는 것으로 가정
        return []

    def get_funding_rates_by_symbol(self, symbol: str, limit: int = 100):
        """
        특정 심볼의 펀딩비 데이터를 최신순으로 가져옵니다.
        """
        return self.db.query(FundingRate).filter(FundingRate.symbol == symbol).order_by(FundingRate.timestamp.desc()).limit(limit).all()

    def get_open_interest_by_symbol(self, symbol: str, limit: int = 100):
        """
        특정 심볼의 미결제 약정 데이터를 최신순으로 가져옵니다.
        """
        return self.db.query(OpenInterest).filter(OpenInterest.symbol == symbol).order_by(OpenInterest.timestamp.desc()).limit(limit).all()

    def get_order_book_depth(self, symbol: str):
        """
        특정 심볼의 오더북 깊이 데이터를 Redis에서 가져옵니다.
        """
        key = f"binance:depth:{symbol.lower()}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def get_recent_trades(self, symbol: str, limit: int = 100):
        """
        특정 심볼의 최근 체결 데이터를 Redis에서 가져옵니다.
        """
        key = f"binance:trades:{symbol.lower()}"
        data = self.redis_client.lrange(key, 0, limit - 1)
        return [json.loads(trade) for trade in data]
