from sqlalchemy import Column, DateTime, String, Float
from . import Base

class FundingRate(Base):
    __tablename__ = 'funding_rates'

    timestamp = Column(DateTime, primary_key=True)
    symbol = Column(String, primary_key=True)
    funding_rate = Column(Float)
