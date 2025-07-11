"""
데이터베이스 관련 데이터 접근을 처리하는 모듈입니다.
SQLAlchemy를 사용하여 PostgreSQL DB와 상호작용합니다.
"""
from sqlalchemy.orm import Session
from app.models.kline import Kline_1m
from app.models.funding_rate import FundingRate
from app.models.open_interest import OpenInterest

class DBRepository:
    """
    데이터베이스 관련 작업을 위한 리포지토리 클래스.
    - `db`: SQLAlchemy 세션 객체
    """
    def __init__(self, db: Session):
        self.db = db

    def get_klines_by_symbol(self, symbol: str, limit: int = 100) -> list[Kline_1m]:
        """
        특정 심볼의 kline 데이터를 최신순으로 가져옵니다.
        - `symbol`: 조회할 심볼 (예: "BTCUSDT")
        - `limit`: 가져올 데이터 개수
        """
        return self.db.query(Kline_1m).filter(Kline_1m.symbol == symbol).order_by(Kline_1m.timestamp.desc()).limit(limit).all()

    def get_funding_rates_by_symbol(self, symbol: str, limit: int = 100) -> list[FundingRate]:
        """
        특정 심볼의 펀딩비 데이터를 최신순으로 가져옵니다.
        - `symbol`: 조회할 심볼 (예: "BTCUSDT")
        - `limit`: 가져올 데이터 개수
        """
        return self.db.query(FundingRate).filter(FundingRate.symbol == symbol).order_by(FundingRate.timestamp.desc()).limit(limit).all()

    def get_open_interest_by_symbol(self, symbol: str, limit: int = 100) -> list[OpenInterest]:
        """
        특정 심볼의 미결제 약정 데이터를 최신순으로 가져옵니다.
        - `symbol`: 조회할 심볼 (예: "BTCUSDT")
        - `limit`: 가져올 데이터 개수
        """
        return self.db.query(OpenInterest).filter(OpenInterest.symbol == symbol).order_by(OpenInterest.timestamp.desc()).limit(limit).all()
