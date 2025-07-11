"""
APScheduler를 사용하여 주기적인 작업을 관리하는 모듈입니다.

- FastAPI 애플리케이션의 lifespan에서 스케줄러를 시작하고 종료합니다.
- 1분마다 주요 심볼의 매매 신호를 분석하고 결과를 Redis에 저장합니다.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import sessionmaker

from app.core.db import engine
from app.services.signal_service import SignalService
from app.services.historical_data_service import HistoricalDataService
from app.services.realtime_data_service import RealtimeDataService
from app.core.db import redis_client

# SQLAlchemy 세션을 스케줄링된 작업 내에서 생성하기 위한 세션 메이커
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

def get_signal_service() -> SignalService:
    """ 스케줄링 작업 내에서 사용할 SignalService 인스턴스를 생성합니다. """
    db = SessionLocal()
    try:
        historical_data_service = HistoricalDataService(db=db)
        realtime_data_service = RealtimeDataService(redis_client=redis_client)
        return SignalService(historical_data_service, realtime_data_service)
    finally:
        db.close()

async def analyze_and_store_signals():
    """
    주요 심볼(BTCUSDT, ETHUSDT)의 매매 신호를 분석하고 결과를 Redis에 저장합니다.
    - 이 함수는 1분마다 주기적으로 실행됩니다.
    """
    symbols = ["BTCUSDT", "ETHUSDT"] # 분석할 심볼 목록
    signal_service = get_signal_service()
    
    print("\n[Scheduled Job] Analyzing trading signals...")
    for symbol in symbols:
        try:
            signal_data = signal_service.get_combined_trading_signal(symbol)
            # 생성된 신호를 Redis에 JSON 형태로 저장
            redis_key = f"trading_signal:{symbol}"
            redis_client.set(redis_key, signal_data.model_dump_json())
            print(f"- {symbol}: {signal_data.signal} (Score: {signal_data.message.split('Score: ')[1].split(')')[0]}) - Stored in Redis")
        except Exception as e:
            print(f"Error analyzing signal for {symbol}: {e}")

def start_scheduler():
    """ 스케줄러를 시작하고, 매매 신호 분석 작업을 1분 간격으로 등록합니다. """
    scheduler.add_job(analyze_and_store_signals, 'interval', minutes=1, id="analyze_signals")
    scheduler.start()
    print("Scheduler started. Signal analysis job is scheduled to run every minute.")

def stop_scheduler():
    """ 애플리케이션 종료 시 스케줄러를 안전하게 종료합니다. """
    scheduler.shutdown()
    print("Scheduler stopped.")

