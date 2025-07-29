"""
데이터베이스 테이블 모델을 정의하는 모듈

SQLAlchemy의 선언적 기반(Declarative Base)을 사용하여 모든 데이터베이스 모델을 관리한다.
모든 테이블 모델은 명확한 한국어 주석과 일관된 네이밍 컨벤션을 따른다.
"""

from sqlalchemy import Column, DateTime, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class OneMinuteCandlestick(Base):
    """1분 캔들스틱 데이터 테이블
    
    암호화폐 1분봉 OHLCV 데이터와 기술적 지표를 저장한다.
    - 기본 가격 데이터 (OHLCV)
    - 이동평균선 지표
    - 모멘텀 오실레이터
    - 변동성 및 추세 지표
    - 볼린저 밴드
    - 거래량 및 가격 분석 지표
    """
    __tablename__ = "klines_1m"
    
    # 기본 키 (Primary Keys)
    timestamp = Column(DateTime, primary_key=True, comment="캔들 타임스탬프")
    symbol = Column(String, primary_key=True, comment="거래 심볼 (예: BTCUSDT)")
    
    # OHLCV 기본 데이터
    open_price = Column(Float, name="open", comment="시가")
    high_price = Column(Float, name="high", comment="고가")
    low_price = Column(Float, name="low", comment="저가")
    close_price = Column(Float, name="close", comment="종가")
    volume = Column(Float, comment="거래량")
    
    # 이동평균선 지표
    exponential_moving_average_20 = Column(
        Float, name="ema_20", nullable=True, comment="20일 지수이동평균"
    )
    simple_moving_average_50 = Column(
        Float, name="sma_50", nullable=True, comment="50일 단순이동평균"
    )
    simple_moving_average_200 = Column(
        Float, name="sma_200", nullable=True, comment="200일 단순이동평균"
    )
    
    # 모멘텀 오실레이터
    relative_strength_index_14 = Column(
        Float, name="rsi_14", nullable=True, comment="14일 상대강도지수"
    )
    stochastic_k = Column(Float, name="stoch_k", nullable=True, comment="스토캐스틱 %K")
    stochastic_d = Column(Float, name="stoch_d", nullable=True, comment="스토캐스틱 %D")
    
    # MACD 지표
    macd_line = Column(Float, name="macd", nullable=True, comment="MACD 라인")
    macd_signal_line = Column(Float, name="macd_signal", nullable=True, comment="MACD 시그널 라인")
    macd_histogram = Column(Float, name="macd_hist", nullable=True, comment="MACD 히스토그램")
    
    # 변동성 및 추세 지표
    average_true_range = Column(Float, name="atr", nullable=True, comment="평균진폭범위")
    average_directional_index = Column(Float, name="adx", nullable=True, comment="평균방향지수")
    
    # 볼린저 밴드
    bollinger_band_upper = Column(Float, name="bb_upper", nullable=True, comment="볼린저 밴드 상단")
    bollinger_band_middle = Column(Float, name="bb_middle", nullable=True, comment="볼린저 밴드 중간")
    bollinger_band_lower = Column(Float, name="bb_lower", nullable=True, comment="볼린저 밴드 하단")
    
    # 거래량 분석
    volume_simple_moving_average_20 = Column(
        Float, name="volume_sma_20", nullable=True, comment="20일 거래량 단순이동평균"
    )
    volume_ratio = Column(Float, nullable=True, comment="거래량 비율")
    
    # 가격 분석
    price_momentum_5m = Column(Float, nullable=True, comment="5분 가격 모멘텀")
    volatility_20d = Column(Float, nullable=True, comment="20일 변동성")


class FundingRate(Base):
    """펀딩 수수료 데이터 테이블
    
    암호화폐 선물 거래의 펀딩 수수료 정보를 저장한다.
    펀딩 수수료는 롱/숏 포지션 간의 균형을 맞추기 위한 수수료이다.
    """
    __tablename__ = "funding_rates"
    
    timestamp = Column(DateTime, primary_key=True, comment="펀딩 수수료 타임스탬프")
    symbol = Column(String, primary_key=True, comment="거래 심볼 (예: BTCUSDT)")
    funding_rate = Column(Float, comment="펀딩 수수료율")


class OpenInterest(Base):
    """미결제약정 데이터 테이블
    
    암호화폐 선물 거래의 미결제약정 정보를 저장한다.
    미결제약정은 아직 청산되지 않은 포지션의 총량을 나타낸다.
    """
    __tablename__ = "open_interest"
    
    timestamp = Column(DateTime, primary_key=True, comment="미결제약정 타임스탬프")
    symbol = Column(String, primary_key=True, comment="거래 심볼 (예: BTCUSDT)")
    open_interest = Column(Float, comment="미결제약정 수량")
