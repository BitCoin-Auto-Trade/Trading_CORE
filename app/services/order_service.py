"""
실시간 거래 주문과 포지션을 관리하는 고도화된 서비스입니다.

주요 특징:
- **타입 안정성**: Pydantic 모델(PositionData)을 사용하여 Redis 데이터의 타입 불일치 문제를 해결합니다.
- **고성능 동시성**: asyncio.gather를 활용하여 다수의 포지션을 병렬로 모니터링합니다.
- **지능형 리스크 관리**: 단순 손절 외에 변동성, 시간 기반의 다각적 포지션 종료 로직을 갖추고 있습니다.
"""
import asyncio
import logging
from redis import Redis
from typing import Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.schemas.core import TradingSignal
from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter
from app.services.signal_service import SignalService

logger = logging.getLogger(__name__)

class PositionData(BaseModel):
    """Redis에 저장되는 포지션 데이터의 타입 안정성을 보장하는 Pydantic 모델"""
    symbol: str
    side: str
    entry_price: float
    position_size: float
    initial_stop_loss: float
    current_stop_loss: float
    initial_risk_distance: float
    trailing_stop_activated: bool = False
    highest_price_so_far: float
    lowest_price_so_far: float
    entry_timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_redis(cls, redis_data: Dict[str, str]) -> "PositionData":
        processed_data = {}
        for key, value in redis_data.items():
            if key == 'trailing_stop_activated':
                processed_data[key] = value.lower() in ('true', '1', 't')
            elif key == 'entry_timestamp':
                processed_data[key] = datetime.fromisoformat(value)
            elif key in ['side', 'symbol']: # These should already be strings
                processed_data[key] = value
            else: # Assume float for other fields
                processed_data[key] = float(value)
        return cls(**processed_data)

    def to_redis_dict(self) -> Dict[str, str]:
        # 모든 필드를 Redis에 저장하기 위해 문자열로 변환
        return {key: str(value) for key, value in self.model_dump().items()}

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

        # --- 리스크 관리 설정 ---
        self.trailing_stop_activation_ratio = 1.5
        self.trailing_stop_atr_multiplier = 2.0
        self.max_position_hold_time = timedelta(hours=4) # 최대 포지션 보유 시간
        self.volatility_exit_threshold = 0.03 # 1분 내 3% 이상 변동 시 청산

    def _get_position_key(self, symbol: str) -> str:
        return f"position:{symbol}"

    async def process_signal(self, signal: TradingSignal):
        position_key = self._get_position_key(signal.symbol)
        if signal.signal in ["BUY", "SELL"] and not self.redis.exists(position_key):
            # TODO: 실제 주문 실행 로직 (binance_adapter.create_order)
            position = PositionData(
                symbol=signal.symbol,
                side="LONG" if signal.signal == "BUY" else "SHORT",
                entry_price=signal.metadata['tech']['close_price'],
                position_size=signal.position_size,
                initial_stop_loss=signal.stop_loss_price,
                current_stop_loss=signal.stop_loss_price,
                initial_risk_distance=abs(signal.stop_loss_price - signal.metadata['tech']['close_price']),
                highest_price_so_far=signal.metadata['tech']['close_price'],
                lowest_price_so_far=signal.metadata['tech']['close_price'],
            )
            self.redis.hmset(position_key, position.to_redis_dict())
            logger.info(f"[{position.symbol}] 신규 포지션 진입: {position.side} @ {position.entry_price}")

    async def monitor_positions(self):
        """모든 활성 포지션을 병렬로, 타입 안전하게 모니터링합니다."""
        while True:
            try:
                position_keys = [key for key in self.redis.keys("position:*")]
                if position_keys:
                    tasks = [self._monitor_single_position(key) for key in position_keys]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for res in results:
                        if isinstance(res, Exception):
                            logger.error(f"포지션 모니터링 중 예외 발생: {res}", exc_info=False)
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}", exc_info=True)
            await asyncio.sleep(self.monitoring_interval)

    async def _monitor_single_position(self, position_key_raw):
        """개별 포지션을 모니터링하고 리스크를 관리합니다."""
        # position_key가 bytes 타입일 경우 str로 디코딩
        position_key = position_key_raw.decode('utf-8') if isinstance(position_key_raw, bytes) else position_key_raw

        raw_data = self.redis.hgetall(position_key)
        if not raw_data:
            return
        
        # 모든 키와 값을 str로 디코딩 (Redis 클라이언트 설정에 따라 이미 디코딩되어 있을 수 있음)
        decoded_data = {k.decode('utf-8') if isinstance(k, bytes) else k: v.decode('utf-8') if isinstance(v, bytes) else v for k, v in raw_data.items()}

        # symbol은 position_key에서 추출하여 decoded_data에 추가
        symbol = position_key.split(':')[1]
        decoded_data['symbol'] = symbol

        position = PositionData.from_redis(decoded_data)

        current_price = await self.binance_adapter.get_current_price(position.symbol)
        if not current_price:
            return

        exit_reason = self._check_exit_conditions(position, current_price)
        if exit_reason:
            self._close_position(position, current_price, exit_reason)
            return

        self._update_trailing_stop(position, current_price)

    def _check_exit_conditions(self, pos: PositionData, price: float) -> Optional[str]:
        """다각적 포지션 종료 조건을 확인합니다."""
        # 1. 기본 손절
        if (pos.side == "LONG" and price <= pos.current_stop_loss) or \
           (pos.side == "SHORT" and price >= pos.current_stop_loss):
            return "STOP_LOSS_HIT"
        
        # 2. 변동성 기반 청산 (구현 예시 - 최근 1분 데이터 필요)
        # klines = self.db_repo.get_klines_by_symbol_as_df(pos.symbol, limit=2)
        # if len(klines) > 1 and abs(klines.iloc[0]['close'] - klines.iloc[1]['close']) / klines.iloc[1]['close'] > self.volatility_exit_threshold:
        #     return "VOLATILITY_EXIT"

        # 3. 시간 기반 청산
        if datetime.utcnow() - pos.entry_timestamp > self.max_position_hold_time:
            return "TIME_LIMIT_EXCEEDED"
            
        return None

    def _close_position(self, pos: PositionData, price: float, reason: str):
        # TODO: 실제 포지션 종료 주문 실행
        profit = (price - pos.entry_price) if pos.side == "LONG" else (pos.entry_price - price)
        result = "PROFIT" if profit >= 0 else "LOSS"
        logger.info(f"[{pos.symbol}] 포지션 종료. 사유: {reason}, 결과: {result}, 수익: {profit:.4f}")
        self.signal_service.update_performance(result)
        self.redis.delete(self._get_position_key(pos.symbol))

    def _update_trailing_stop(self, pos: PositionData, price: float):
        """동적 손절 로직을 업데이트합니다."""
        key = self._get_position_key(pos.symbol)
        # 트레일링 스탑 활성화 조건
        if not pos.trailing_stop_activated:
            activation_price_long = pos.entry_price + (pos.initial_risk_distance * self.trailing_stop_activation_ratio)
            activation_price_short = pos.entry_price - (pos.initial_risk_distance * self.trailing_stop_activation_ratio)
            if (pos.side == "LONG" and price >= activation_price_long) or \
               (pos.side == "SHORT" and price <= activation_price_short):
                pos.trailing_stop_activated = True
                self.redis.hset(key, "trailing_stop_activated", str(True))
                logger.info(f"[{pos.symbol}] 동적 익절(Trailing Stop) 활성화.")

        # 활성화된 경우, 손절선 업데이트
        if pos.trailing_stop_activated:
            atr_val = pos.initial_risk_distance # 단순화를 위해 초기 리스크 사용
            new_stop_loss = pos.current_stop_loss
            if pos.side == "LONG":
                highest = max(pos.highest_price_so_far, price)
                self.redis.hset(key, "highest_price_so_far", str(highest))
                new_stop_loss = highest - (atr_val * self.trailing_stop_atr_multiplier)
                if new_stop_loss > pos.current_stop_loss:
                    self.redis.hset(key, "current_stop_loss", str(new_stop_loss))
                    logger.info(f"[{pos.symbol}] 롱 포지션 손절선 상향: {new_stop_loss:.4f}")
            else: # SHORT
                lowest = min(pos.lowest_price_so_far, price)
                self.redis.hset(key, "lowest_price_so_far", str(lowest))
                new_stop_loss = lowest + (atr_val * self.trailing_stop_atr_multiplier)
                if new_stop_loss < pos.current_stop_loss:
                    self.redis.hset(key, "current_stop_loss", str(new_stop_loss))
                    logger.info(f"[{pos.symbol}] 숏 포지션 손절선 하향: {new_stop_loss:.4f}")