"""
APScheduler를 사용하여 주기적인 작업을 관리하는 모듈입니다.

- FastAPI 애플리케이션의 생명주기(lifespan)에서 스케줄러를 시작하고 종료합니다.
- 매 분 정해진 시간에 주요 심볼의 매매 신호를 분석하고 OrderService로 전달합니다.
"""

import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.services.signal_service import SignalService
from app.services.order_service import OrderService
from app.utils.logging import get_logger

logger = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

async def process_signals_for_entry(signal_service: SignalService, order_service: OrderService):
    """
    설정에 정의된 모든 심볼의 매매 신호를 분석하고, 자동 거래가 활성화된 경우 API를 호출합니다.
    이 함수는 스케줄러에 의해 주기적으로 실행됩니다.
    """
    # 자동 거래 상태 확인
    auto_trading_enabled = signal_service.settings.AUTO_TRADING_ENABLED
    
    symbols = [symbol.strip() for symbol in settings.TRADING_SYMBOLS.split(",")]
    
    logger.info(f"[스케줄링 작업] {len(symbols)}개 심볼의 포지션 진입 신호 분석을 시작합니다... (자동거래: {'ON' if auto_trading_enabled else 'OFF'})")

    for symbol in symbols:
        try:
            signal_data = signal_service.get_combined_trading_signal(symbol)
            
            # Redis에 신호 저장
            redis_key = f"trading_signal:{symbol}"
            try:
                signal_service.redis_client.setex(redis_key, 3600, json.dumps(signal_data.model_dump(), default=str))
            except Exception as e:
                logger.error(f"Redis에 신호 저장 실패 [{symbol}]: {e}")
            
            if signal_data.signal != "HOLD":
                confidence_str = f"{signal_data.confidence_score:.2f}" if signal_data.confidence_score is not None else "N/A"
                
                if auto_trading_enabled:
                    # 자동 거래 활성화 시 주문 실행
                    await order_service.process_signal(signal_data)
                    logger.info(f"  - [{symbol}] 신호: {signal_data.signal}, 점수: {confidence_str} (자동 주문 실행됨)")
                else:
                    # 자동 거래 비활성화 시 신호만 기록
                    logger.info(f"  - [{symbol}] 신호: {signal_data.signal}, 점수: {confidence_str} (자동거래 비활성화됨)")
            else:
                confidence_str = f"{signal_data.confidence_score:.2f}" if signal_data.confidence_score is not None else "N/A"
                logger.info(f"  - [{symbol}] 신호: HOLD, 점수: {confidence_str} (진입 조건 미충족)")

        except Exception as e:
            logger.error(f"[{symbol}] 신호 분석 중 오류 발생: {e}", exc_info=True)

def start_scheduler(signal_service: SignalService, order_service: OrderService):
    """
    APScheduler를 시작하고, 매매 신호 분석 작업을 등록합니다.
    작업은 매 분 5초에 실행되도록 설정됩니다.
    """
    scheduler.add_job(process_signals_for_entry, "cron", second=5, id="process_signals", args=[signal_service, order_service])
    scheduler.start()
    logger.info("스케줄러가 시작되었습니다. 매 분 5초에 신호 분석 작업이 실행됩니다.")

def stop_scheduler():
    """
    애플리케이션 종료 시 APScheduler를 안전하게 종료합니다.
    """
    scheduler.shutdown()
    logger.info("스케줄러가 중지되었습니다.")
