
"""
실시간으로 거래 주문과 현재 포지션을 관리하는 서비스입니다.

- SignalService로부터 신호를 받아 포지션 진입/종료를 결정합니다.
- Redis를 사용하여 현재 포지션 상태를 지속적으로 관리합니다.
- 백그라운드에서 실행되며, 실시간 가격 변동에 따라 동적 익절(Trailing Stop) 로직을 수행합니다.
"""
import asyncio
import logging
from redis import Redis
from app.schemas.core import TradingSignal
from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter
from app.services.signal_service import SignalService

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(
        self,
        db_repository: DBRepository,
        binance_adapter: BinanceAdapter,
        signal_service: SignalService,
        redis_client: Redis,
    ):
        self.db_repo = db_repository
        self.binance_adapter = binance_adapter
        self.signal_service = signal_service
        self.redis = redis_client
        self.monitoring_interval = 5  # 포지션 감시 주기 (초)

        # --- 동적 익절(Trailing Stop) 설정 ---
        # 이익이 초기 손절폭의 N배에 도달했을 때 트레일링 스탑 활성화
        self.trailing_stop_activation_ratio = 1.5
        # 고점/저점 대비 N * ATR 만큼 떨어진 지점에 손절선 설정
        self.trailing_stop_atr_multiplier = 2.0

    def _get_position_key(self, symbol: str) -> str:
        """Redis에서 포지션 정보를 저장하기 위한 키를 반환합니다."""
        return f"position:{symbol}"

    async def process_signal(self, signal: TradingSignal):
        """
        SignalService로부터 받은 신호를 처리하여 포지션 진입 또는 상태 업데이트를 수행합니다.
        """
        position_key = self._get_position_key(signal.symbol)
        existing_position = self.redis.exists(position_key)

        # 매수/매도 신호가 있고, 현재 포지션이 없을 때만 신규 진입
        if signal.signal in ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL"] and not existing_position:
            # TODO: 실제 주문 실행 로직 추가 (binance_adapter.create_order)
            
            side = "LONG" if "BUY" in signal.signal else "SHORT"
            entry_price = signal.metadata['tech']['close_price']
            initial_stop_loss = signal.stop_loss_price
            position_size = signal.position_size
            initial_risk_distance = abs(initial_stop_loss - entry_price)

            position_data = {
                "side": side,
                "entry_price": float(entry_price),
                "position_size": float(position_size),
                "initial_stop_loss": float(initial_stop_loss),
                "current_stop_loss": float(initial_stop_loss),
                "initial_risk_distance": float(initial_risk_distance),
                "trailing_stop_activated": "False",
                "highest_price_so_far": float(entry_price),
                "lowest_price_so_far": float(entry_price),
            }
            self.redis.hmset(position_key, position_data)
            logger.info(
                f"[{signal.symbol}] 신규 포지션 진입 | 방향: {side} | "
                f"진입가: {float(entry_price):.4f} | 초기 손절가: {float(initial_stop_loss):.4f} | "
                f"수량: {float(position_size)}"
            )

    async def monitor_positions(self):
        """
        백그라운드에서 주기적으로 실행되며, 모든 활성 포지션을 감시하고 관리합니다.
        """
        while True:
            try:
                position_keys = self.redis.keys("position:*")
                if not position_keys:
                    await asyncio.sleep(self.monitoring_interval)
                    continue

                for key in position_keys:
                    symbol = key.split(":")[1]
                    position = self.redis.hgetall(key)
                    
                    current_price = await self.binance_adapter.get_current_price(symbol)
                    if not current_price:
                        continue

                    side = position["side"]
                    entry_price = float(position["entry_price"])
                    current_stop_loss = float(position["current_stop_loss"])
                    trailing_activated = position["trailing_stop_activated"] == 'True'
                    
                    # 1. 포지션 종료 조건 확인 (손절 또는 동적 익절)
                    if (side == "LONG" and current_price <= current_stop_loss) or \
                       (side == "SHORT" and current_price >= current_stop_loss):
                        
                        # TODO: 실제 포지션 종료 주문 실행
                        
                        if trailing_activated:
                            # 동적 익절(수익 실현)
                            profit = (current_price - entry_price) if side == "LONG" else (entry_price - current_price)
                            logger.info(
                                f"💰 [{symbol}] 동적 익절(수�� 실현) | 방향: {side} | "
                                f"진입가: {entry_price:.4f} | 종료가: {current_price:.4f} | "
                                f"수익: ${profit:.4f}"
                            )
                            self.signal_service.update_performance("PROFIT")
                        else:
                            # 초기 손절
                            loss = (current_price - entry_price) if side == "LONG" else (entry_price - current_price)
                            logger.warning(
                                f"ኪ [{symbol}] 초기 손절 | 방향: {side} | "
                                f"진입가: {entry_price:.4f} | 종료가: {current_price:.4f} | "
                                f"손실: ${loss:.4f}"
                            )
                            self.signal_service.update_performance("LOSS")
                        
                        self.redis.delete(key)
                        continue

                    # 2. 동적 익절(Trailing Stop) 로직
                    # 2a. 트레일링 스탑 활성화 조건 체크
                    if not trailing_activated:
                        initial_risk_distance = float(position["initial_risk_distance"])
                        activation_price_long = entry_price + (initial_risk_distance * self.trailing_stop_activation_ratio)
                        activation_price_short = entry_price - (initial_risk_distance * self.trailing_stop_activation_ratio)

                        if (side == "LONG" and current_price >= activation_price_long) or \
                           (side == "SHORT" and current_price <= activation_price_short):
                            self.redis.hset(key, "trailing_stop_activated", "True")
                            trailing_activated = True
                            logger.info(f"[{symbol}] 동적 익절(Trailing Stop) 활성화. 현재가: {current_price}")

                    # 2b. 활성화된 경우, 손절선 업데이트
                    if trailing_activated:
                        # ATR 값 가져오기 (실제로는 kline 데이터에서 다시 계산해야 함)
                        # 여기서는 임시로 initial_risk_distance 사용
                        atr_val = float(position["initial_risk_distance"])

                        if side == "LONG":
                            highest_price = max(float(position["highest_price_so_far"]), current_price)
                            self.redis.hset(key, "highest_price_so_far", highest_price)
                            
                            new_stop_loss = highest_price - (atr_val * self.trailing_stop_atr_multiplier)
                            if new_stop_loss > current_stop_loss:
                                self.redis.hset(key, "current_stop_loss", new_stop_loss)
                                logger.info(f"[{symbol}] 롱 포지션 손절선 상향 조정: {new_stop_loss:.4f}")

                        elif side == "SHORT":
                            lowest_price = min(float(position["lowest_price_so_far"]), current_price)
                            self.redis.hset(key, "lowest_price_so_far", lowest_price)

                            new_stop_loss = lowest_price + (atr_val * self.trailing_stop_atr_multiplier)
                            if new_stop_loss < current_stop_loss:
                                self.redis.hset(key, "current_stop_loss", new_stop_loss)
                                logger.info(f"[{symbol}] 숏 포지션 손절선 하향 조정: {new_stop_loss:.4f}")

            except Exception as e:
                logger.error(f"포지션 모니터링 중 오류 발생: {e}", exc_info=True)
            
            await asyncio.sleep(self.monitoring_interval)
