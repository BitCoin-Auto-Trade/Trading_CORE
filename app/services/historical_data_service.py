"""
과거 데이터 관련 비즈니스 로직을 처리하는 서비스 모듈입니다.
"""
from sqlalchemy.orm import Session
from app.repository.db_repository import DBRepository
from app.schemas.getdata_schema import KlineBase, FundingRateBase, OpenInterestBase

class HistoricalDataService:
    """
    과거 데이터 조회를 위한 서비스 클래스.
    - `db_repo`: DBRepository 인스턴스
    """
    def __init__(self, db: Session):
        self.db_repo = DBRepository(db=db)

    def get_klines_data(self, symbol: str, limit: int) -> list[KlineBase]:
        """
        특정 심볼의 과거 kline 데이터를 조회합니다.
        """
        return self.db_repo.get_klines_by_symbol(symbol, limit)

    def get_funding_rates_data(self, symbol: str, limit: int) -> list[FundingRateBase]:
        """
        특정 심볼의 과거 펀딩비 데이터를 조회합니다.
        """
        return self.db_repo.get_funding_rates_by_symbol(symbol, limit)

    def get_open_interest_data(self, symbol: str, limit: int) -> list[OpenInterestBase]:
        """
        특정 심볼의 과거 미결제 약정 데이터를 조회합니다.
        """
        return self.db_repo.get_open_interest_by_symbol(symbol, limit)
