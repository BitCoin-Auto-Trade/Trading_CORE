from sqlalchemy.orm import Session
from app.models.kline import Kline_1m
from app.models.funding_rate import FundingRate
from app.models.open_interest import OpenInterest

class SignalRepository:
    def get_klines_by_symbol(self, db: Session, symbol: str, limit: int = 100):
        """
        특정 심볼의 kline 데이터를 최신순으로 가져옵니다.
        """
        return db.query(Kline_1m).filter(Kline_1m.symbol == symbol).order_by(Kline_1m.timestamp.desc()).limit(limit).all()

    def get_funding_rates_by_symbol(self, db: Session, symbol: str, limit: int = 100):
        """
        특정 심볼의 펀딩비 데이터를 최신순으로 가져옵니다.
        """
        return db.query(FundingRate).filter(FundingRate.symbol == symbol).order_by(FundingRate.timestamp.desc()).limit(limit).all()

    def get_open_interest_by_symbol(self, db: Session, symbol: str, limit: int = 100):
        """
        특정 심볼의 미결제 약정 데이터를 최신순으로 가져옵니다.
        """
        return db.query(OpenInterest).filter(OpenInterest.symbol == symbol).order_by(OpenInterest.timestamp.desc()).limit(limit).all()
