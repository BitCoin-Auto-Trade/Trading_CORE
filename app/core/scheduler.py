"""
APScheduler를 사용하여 주기적인 작업을 관리하는 모듈입니다.

- FastAPI 애플리케이션의 생명주기(lifespan)에서 스케줄러를 시작하고 종료합니다.
- 매 분 정해진 시간에 주요 심볼의 매매 신호를 분석하고 결과를 Redis에 저장합니다.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import sessionmaker

from app.core.db import engine, redis_client
from app.core.config import settings
from app.services.signal_service import SignalService
from app.adapters.binance_adapter import BinanceAdapter
from app.repository.db_repository import DBRepository

logger = logging.getLogger(__name__)

# 스케줄링된 작업 내에서 독립적인 DB 세션을 생성하기 위한 세션 메이커입니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def get_signal_service() -> tuple[SignalService, DBRepository]:
    """
    스케줄링 작업 내에서 사용할 SignalService 인스턴스와 DBRepository를 생성하여 반환합니다.
    주의: 이 함수는 호출될 때마다 새로운 DB 세션을 생성하므로,
    반환된 서비스 사용 후에는 반드시 DB 세션을 닫아야 합니다.
    """
    db = SessionLocal()
    try:
        db_repo = DBRepository(db=db)
        binance_adapter = BinanceAdapter(db=db, redis_client=redis_client)
        signal_service = SignalService(db_repository=db_repo, binance_adapter=binance_adapter)
        return signal_service, db_repo
    except Exception as e:
        db.close()
        logger.error(f"SignalService 생성 실패: {e}", exc_info=True)
        raise


async def analyze_and_store_signals():
    """
    설정에 정의된 모든 심볼의 매매 신호를 분석하고, 그 결과를 Redis에 저장합니다.
    이 함수는 스케줄러에 의해 주기적으로 실행됩니다.
    """
    symbols = [symbol.strip() for symbol in settings.TRADING_SYMBOLS.split(",")]
    signal_service, db_repo = None, None
    try:
        signal_service, db_repo = get_signal_service()
        logger.info(f"\n[스케줄링 작업] {len(symbols)}개 심볼의 매매 신호 분석을 시작합니다...")

        for symbol in symbols:
            try:
                signal_data = signal_service.get_combined_trading_signal(symbol)
                redis_key = f"trading_signal:{symbol}"
                redis_client.set(redis_key, signal_data.model_dump_json())
                logger.info(
                    f"  - [{symbol}] 신호: {signal_data.signal}, 점수: {signal_data.confidence_score:.2f} (Redis 저장 완료)"
                )
            except Exception as e:
                logger.error(f"[{symbol}] 신호 분석 중 오류 발생: {e}", exc_info=True)

    finally:
        if db_repo:
            db_repo.db.close()
            logger.debug("DB 세션이 성공적으로 종료되었습니다.")


def start_scheduler():
    """
    APScheduler를 시작하고, 매매 신호 분석 작업을 등록합니다.
    작업은 매 분 5초에 실행되도록 설정됩니다.
    """
    # NOTE: "cron" 대신 "interval"을 사용하면 서버 시작 후 즉시 첫 실행을 보장할 수 있습니다.
    # 예를 들어, 매 1분마다 실행: scheduler.add_job(analyze_and_store_signals, "interval", minutes=1, id="analyze_signals")
    scheduler.add_job(analyze_and_store_signals, "cron", second=5, id="analyze_signals")
    scheduler.start()
    logger.info("스케줄러가 시작되었습니다. 매 분 5초에 신호 분석 작업이 실행됩니다.")


def stop_scheduler():
    """
    애플리케이션 종료 시 APScheduler를 안전하게 종료합니다.
    """
    scheduler.shutdown()
    logger.info("스케줄러가 중지되었습니다.")