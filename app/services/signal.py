from sqlalchemy.orm import Session
from app.repository.signal import SignalRepository

class SignalService:
    def __init__(self, db: Session):
        self.db = db
        self.signal_repo = SignalRepository()

    def get_klines(self, symbol: str, limit: int):
        """
        특정 심볼의 kline 데이터를 조회합니다.
        """
        return self.signal_repo.get_klines_by_symbol(self.db, symbol, limit)

    def get_funding_rates(self, symbol: str, limit: int):
        """
        특정 심볼의 펀딩비 데이터를 조회합니다.
        """
        return self.signal_repo.get_funding_rates_by_symbol(self.db, symbol, limit)

    def get_open_interest(self, symbol: str, limit: int):
        """
        특정 심볼의 미결제 약정 데이터를 조회합니다.
        """
        return self.signal_repo.get_open_interest_by_symbol(self.db, symbol, limit)
