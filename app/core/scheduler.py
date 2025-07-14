
"""
APScheduler를 사용하여 주기적인 작업을 관리하는 모듈입니다.

- FastAPI 애플리케이션의 생명주기(lifespan)에서 스케줄러를 시작하고 종료합니다.
- 매 분 정해진 시간에 주요 심볼의 매매 신호를 분석하고 OrderService로 전달합니다.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import sessionmaker

from app.core.db import engine, redis_client
from app.core.config import settings
from app.services.signal_service import SignalService
from app.services.order_service import OrderService
from app.adapters.binance_adapter import BinanceAdapter
from app.repository.db_repository import DBRepository

logger = logging.getLogger(__name__)

# 스케줄링된 작업 내에서 독립적인 DB 세션을 생성하기 위한 세션 메이커입니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def get_services() -> tuple[SignalService, OrderService, DBRepository]:
    """
    스케줄링 작업 내에서 사용할 서비스 인스턴스들을 생성하여 반환합니다.
    주의: 이 함수는 호출될 때마다 새로운 DB 세션을 생성하므로,
    반환된 서비스 사용 후에는 반드시 DB 세션을 닫아야 합니다.
    """
    db = SessionLocal()
    try:
        db_repo = DBRepository(db=db)
        binance_adapter = BinanceAdapter(db=db, redis_client=redis_client)
        signal_service = SignalService(db_repository=db_repo, binance_adapter=binance_adapter, redis_client=redis_client)
        order_service = OrderService(
            db_repository=db_repo,
            binance_adapter=binance_adapter,
            signal_service=signal_service,
            redis_client=redis_client,
        )
        return signal_service, order_service, db_repo
    except Exception as e:
        db.close()
        logger.error(f"서비스 생성 실패: {e}", exc_info=True)
        raise


async def process_signals_for_entry():
    """
    설정에 정의된 모든 심볼의 매매 신호를 분석하고, 그 결과를 OrderService로 전달합니다.
    이 함수는 스케줄러에 의해 주기적으로 실행됩니다.
    """
    symbols = [symbol.strip() for symbol in settings.TRADING_SYMBOLS.split(",")]
    signal_service, order_service, db_repo = None, None, None
    try:
        signal_service, order_service, db_repo = get_services()
        logger.info(f"[스케줄링 작업] {len(symbols)}개 심볼의 포지션 진입 신호 분석을 시작합니다...")

        for symbol in symbols:
            try:
                signal_data = signal_service.get_combined_trading_signal(symbol)
                if signal_data.signal != "HOLD":
                    await order_service.process_signal(signal_data)
                    logger.info(
                        f"  - [{symbol}] 신호: {signal_data.signal}, 점수: {signal_data.confidence_score:.2f} (OrderService 전달 완료)"
                    )
                else:
                    logger.info(
                        f"  - [{symbol}] 신호: HOLD, 점수: {signal_data.confidence_score:.2f} (진입 조건 미충족)"
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
    scheduler.add_job(process_signals_for_entry, "cron", second=5, id="process_signals")
    scheduler.start()
    logger.info("스케줄러가 시작되었습니다. 매 분 5초에 신호 분석 작업이 실행됩니다.")


def stop_scheduler():
    """
    애플리케이션 종료 시 APScheduler를 안전하게 종료합니다.
    """
    scheduler.shutdown()
    logger.info("스케줄러가 중지되었습니다.")
