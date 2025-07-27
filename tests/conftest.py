"""
테스트 설정 및 공통 유틸리티
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.db import get_db, get_redis

# 테스트용 인메모리 데이터베이스
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """테스트용 DB 세션"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_redis():
    """테스트용 Redis 클라이언트 모ック"""
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.ping.return_value = True
    return mock_redis

# 의존성 오버라이드
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis

@pytest.fixture
def client():
    """테스트 클라이언트"""
    return TestClient(app)

@pytest.fixture
def mock_redis():
    """Redis 모ック"""
    return override_get_redis()

@pytest.fixture
def mock_binance_adapter():
    """Binance Adapter 모크"""
    with patch('app.adapters.binance_adapter.BinanceAdapter') as mock:
        adapter = Mock()
        adapter.get_kline_1m.return_value = []
        adapter.get_orderbook.return_value = {"bids": [], "asks": []}
        adapter.create_order.return_value = {"orderId": "123456", "status": "FILLED"}
        mock.return_value = adapter
        yield adapter

@pytest.fixture
def event_loop():
    """이벤트 루프 픽스처"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

class TestConfig:
    """테스트 설정"""
    TESTING = True
    DATABASE_URL = SQLALCHEMY_DATABASE_URL
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 1  # 테스트용 DB
