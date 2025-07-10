from sqlalchemy import Column, DateTime, String, Float
from . import Base

class OpenInterest(Base):
    __tablename__ = 'open_interest'

    timestamp = Column(DateTime, primary_key=True)
    symbol = Column(String, primary_key=True)
    open_interest = Column(Float)
