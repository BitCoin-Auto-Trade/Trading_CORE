
"""
실시간 거래 주문과 포지션을 관리하는 고도화된 서비스입니다.

주요 특징:
- **타입 안정성**: Pydantic 모델(PositionData)을 사용하여 Redis 데이터의 타입 불일치 문제를 해결합니다.
- **고성능 동시성**: asyncio.gather를 활용하여 다수의 포지션을 병렬로 모니터링합니다.
- **지능형 리스크 관리**: 단순 손절 외에 변동성, 시간 기반의 다각적 포지션 종료 로직을 갖추고 있습니다.
"""
import asyncio
import json
from redis import Redis
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.schemas.core import TradingSignal, TradingSettings
from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter
from app.services.signal_service import SignalService
from app.core.constants import REDIS_KEYS, TRADING, DEFAULTS
from app.core.exceptions import PositionException, OrderServiceException
from app.utils.helpers import (
    safe_float_conversion, 
    safe_bool_conversion, 
    get_redis_key,
    validate_symbol,
    create_api_response,
    retry_on_failure,
    timeout
)
from app.utils.redis_settings import parse_redis_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

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
        """Redis 데이터에서 PositionData 객체를 생성합니다."""
        processed_data = {}
        for key, value in redis_data.items():
            if key == 'trailing_stop_activated':
                processed_data[key] = safe_bool_conversion(value)
            elif key == 'entry_timestamp':
                processed_data[key] = datetime.fromisoformat(value)
            elif key in ['side', 'symbol']:
                processed_data[key] = value
            else:
                processed_data[key] = safe_float_conversion(value)
        return cls(**processed_data)

    def to_redis_dict(self) -> Dict[str, str]:
        """Redis 저장을 위해 모든 필드를 문자열로 변환합니다."""
        return {key: str(value) for key, value in self.model_dump().items()}
    
    def calculate_profit_loss(self, current_price: float) -> float:
        """현재 가격 기준으로 손익을 계산합니다."""
        if self.side == TRADING["SIDES"]["LONG"]:
            return current_price - self.entry_price
        else:
            return self.entry_price - current_price
    
    def get_unrealized_pnl_percentage(self, current_price: float) -> float:
        """미실현 손익을 백분율로 계산합니다."""
        pnl = self.calculate_profit_loss(current_price)
        return (pnl / self.entry_price) * 100

class OrderService:
    """주문 및 포지션 관리 서비스"""
    
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
        self.monitoring_interval = DEFAULTS["MONITORING_INTERVAL"]

        # 동적 거래 설정 로드
        self._load_settings()

        # 리스크 관리 설정
        self.max_position_hold_time = timedelta(hours=DEFAULTS["MAX_POSITION_HOLD_HOURS"])
        self.volatility_exit_threshold = DEFAULTS["VOLATILITY_EXIT_THRESHOLD"]

    def _load_settings(self):
        """Redis에서 거래 설정을 불러오거나, 없으면 기본값을 사용합니다."""
        settings_data = self.redis.hgetall(REDIS_KEYS["TRADING_SETTINGS"])
        if settings_data:
            logger.debug("Redis에서 거래 설정을 불러옵니다.")
            # Redis에서 가져온 데이터를 적절한 타입으로 파싱
            parsed_settings = parse_redis_settings(settings_data)
            self.settings = TradingSettings.model_validate(parsed_settings)
        else:
            logger.debug("기본 거래 설정을 사용합니다.")
            self.settings = TradingSettings()

    def _get_position_key(self, symbol: str) -> str:
        """포지션 키를 생성합니다."""
        return get_redis_key("POSITION", symbol)

    def get_all_positions(self) -> List[PositionData]:
        """모든 활성 포지션을 조회합니다."""
        try:
            positions = []
            # Redis에서 모든 포지션 키를 찾습니다
            position_pattern = f"{REDIS_KEYS['POSITION_PREFIX']}*"
            position_keys = self.redis.keys(position_pattern)
            
            for key in position_keys:
                try:
                    position_data = self.redis.hgetall(key)
                    if position_data:
                        position = PositionData.from_redis(position_data)
                        positions.append(position)
                except Exception as e:
                    logger.warning(f"포지션 데이터 파싱 실패: {key}, 오류: {e}")
                    continue
                    
            return positions
        except Exception as e:
            logger.error(f"포지션 조회 중 오류 발생: {e}")
            return []

    @retry_on_failure(max_retries=3, delay=1.0)
    async def process_signal(self, signal: TradingSignal) -> Dict[str, any]:
        """매매 신호를 처리하고 포지션을 생성합니다."""
        symbol = validate_symbol(signal.symbol)
        position_key = self._get_position_key(symbol)
        
        # 이미 포지션이 존재하는지 확인
        if self.redis.exists(position_key):
            logger.warning(f"이미 활성 포지션이 존재합니다", symbol=symbol)
            return create_api_response(
                success=False,
                message=f"{symbol} 포지션이 이미 존재합니다"
            )
            
        if signal.signal in [TRADING["SIGNALS"]["BUY"], TRADING["SIGNALS"]["SELL"]]:
            position = self._create_position_from_signal(signal)
            
            # Redis에 포지션 저장
            self.redis.hset(position_key, mapping=position.to_redis_dict())
            
            logger.log_position(
                symbol=symbol,
                action="OPENED",
                details={
                    "side": position.side,
                    "entry_price": position.entry_price,
                    "position_size": position.position_size,
                    "stop_loss": position.initial_stop_loss
                }
            )
            
            return create_api_response(
                message=f"{symbol} 포지션 생성 성공",
                data=position.model_dump()
            )

    def _create_position_from_signal(self, signal: TradingSignal) -> PositionData:
        """거래 신호에서 포지션 데이터를 생성합니다."""
        close_price = signal.metadata.get('tech', {}).get('close_price')
        if not close_price:
            raise OrderServiceException("신호에 종가 정보가 없습니다")
        
        # 기본값 설정
        position_size = signal.position_size or DEFAULTS["POSITION_SIZE"]
        stop_loss_price = signal.stop_loss_price or close_price * (1 - DEFAULTS["STOP_LOSS_RATIO"])
        
        return PositionData(
            symbol=signal.symbol,
            side=TRADING["SIDES"]["LONG"] if signal.signal == TRADING["SIGNALS"]["BUY"] else TRADING["SIDES"]["SHORT"],
            entry_price=close_price,
            position_size=position_size,
            initial_stop_loss=stop_loss_price,
            current_stop_loss=stop_loss_price,
            initial_risk_distance=abs(stop_loss_price - close_price),
            highest_price_so_far=close_price,
            lowest_price_so_far=close_price,
        )

    async def monitor_positions(self):
        """모든 활성 포지션을 병렬로, 타입 안전하게 모니터링합니다."""
        logger.info("포지션 모니터링 시작")
        
        while True:
            try:
                position_keys = self._get_all_position_keys()
                
                if position_keys:
                    logger.debug(f"{len(position_keys)}개 포지션 모니터링 중")
                    tasks = [self._monitor_single_position(key) for key in position_keys]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # 결과 처리 및 상세 오류 로깅
                    errors = [res for res in results if isinstance(res, Exception)]
                    if errors:
                        logger.warning(f"포지션 모니터링 중 {len(errors)}개 오류 발생")
                        for i, error in enumerate(errors):
                            logger.error(f"포지션 모니터링 오류 {i+1}: {type(error).__name__}: {str(error)}")
                            # 필요시 스택 트레이스 포함
                            if hasattr(error, '__traceback__'):
                                import traceback
                                logger.debug(f"오류 스택 트레이스: {traceback.format_exception(type(error), error, error.__traceback__)}")
                        
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                
            await asyncio.sleep(self.monitoring_interval)

    def _get_all_position_keys(self) -> List[str]:
        """모든 포지션 키를 가져옵니다."""
        return [key for key in self.redis.keys(f"{REDIS_KEYS['POSITION']}*")]

    @timeout(timeout_seconds=30)
    async def _monitor_single_position(self, position_key_raw):
        """개별 포지션을 모니터링하고 리스크를 관리합니다."""
        try:
            position_key = position_key_raw.decode('utf-8') if isinstance(position_key_raw, bytes) else position_key_raw
            
            # 포지션 데이터 로드
            position = self._load_position_from_redis(position_key)
            if not position:
                logger.debug(f"포지션 데이터 없음: {position_key}")
                return
            
            # Binance API 사용 가능 여부 확인
            if not self.binance_adapter.is_api_available():
                logger.debug(f"Binance API 비활성화, 포지션 모니터링 건너뜀: {position.symbol}")
                return
            
            # 현재 가격 조회
            current_price = await self.binance_adapter.get_current_price(position.symbol)
            if not current_price:
                logger.warning(f"현재 가격 조회 실패", symbol=position.symbol)
                return

            # 종료 조건 확인
            exit_reason = self._check_exit_conditions(position, current_price)
            if exit_reason:
                await self._close_position(position, current_price, exit_reason)
                return

            # 트레일링 스탑 업데이트
            await self._update_trailing_stop(position, current_price)
            
        except Exception as e:
            # 개별 포지션 모니터링 오류를 상위로 전파하지 않고 로깅만 수행
            logger.error(f"포지션 모니터링 개별 오류 ({position_key_raw}): {type(e).__name__}: {str(e)}")
            raise  # gather에서 exception으로 수집되도록 raise

    def _load_position_from_redis(self, position_key: str) -> Optional[PositionData]:
        """Redis에서 포지션 데이터를 로드합니다."""
        try:
            raw_data = self.redis.hgetall(position_key)
            if not raw_data:
                logger.debug(f"Redis에서 포지션 데이터 없음: {position_key}")
                return None
            
            # 데이터 디코딩
            decoded_data = {
                k.decode('utf-8') if isinstance(k, bytes) else k: 
                v.decode('utf-8') if isinstance(v, bytes) else v 
                for k, v in raw_data.items()
            }
            
            # 심볼 추출
            symbol_parts = position_key.split(':')
            if len(symbol_parts) < 2:
                logger.error(f"잘못된 포지션 키 형식: {position_key}")
                return None
                
            symbol = symbol_parts[1]
            decoded_data['symbol'] = symbol
            
            return PositionData.from_redis(decoded_data)
            
        except Exception as e:
            logger.error(f"포지션 데이터 로드 실패 ({position_key}): {type(e).__name__}: {str(e)}")
            return None

    def _check_exit_conditions(self, pos: PositionData, price: float) -> Optional[str]:
        """다각적 포지션 종료 조건을 확인합니다."""
        # 1. 기본 손절
        if (pos.side == TRADING["SIDES"]["LONG"] and price <= pos.current_stop_loss) or \
           (pos.side == TRADING["SIDES"]["SHORT"] and price >= pos.current_stop_loss):
            return TRADING["CLOSE_REASONS"]["STOP_LOSS_HIT"]
        
        # 2. 시간 기반 청산
        if datetime.utcnow() - pos.entry_timestamp > self.max_position_hold_time:
            return TRADING["CLOSE_REASONS"]["TIME_LIMIT_EXCEEDED"]
        
        # 3. 변동성 기반 청산 - ATR을 활용한 변동성 임계값 체크
        try:
            # Redis에서 현재 ATR 값을 가져와서 변동성 기반 청산 조건 체크
            atr_key = f"{REDIS_KEYS['PRICE_PREFIX']}{pos.symbol}:atr"
            current_atr = self.redis.get(atr_key)
            if current_atr:
                current_atr = float(current_atr)
                price_change_ratio = abs(price - pos.entry_price) / pos.entry_price
                # ATR 대비 가격 변동이 너무 클 경우 강제 청산
                if price_change_ratio > (current_atr * self.volatility_exit_threshold):
                    return TRADING["CLOSE_REASONS"]["HIGH_VOLATILITY"]
        except Exception as e:
            logger.warning(f"변동성 기반 청산 조건 체크 실패: {e}")
        
        return None

    async def _close_position(self, pos: PositionData, price: float, reason: str):
        """포지션을 종료합니다."""
        try:
            # 실제 거래소에서 포지션 종료 주문 실행
            order_result = await self.binance_adapter.close_position(
                symbol=pos.symbol
            )
            
            profit = pos.calculate_profit_loss(price)
            result = TRADING["RESULTS"]["PROFIT"] if profit >= 0 else TRADING["RESULTS"]["LOSS"]
            
            # 성능 업데이트
            self.signal_service.update_performance(result)
            
            # Redis에서 포지션 삭제
            self.redis.delete(self._get_position_key(pos.symbol))
            
            logger.log_position(
                symbol=pos.symbol,
                action="CLOSED",
                details={
                    "reason": reason,
                    "result": result,
                    "profit": profit,
                    "close_price": price,
                    "pnl_percentage": pos.get_unrealized_pnl_percentage(price),
                    "order_id": order_result.get("orderId") if order_result else None
                }
            )
            
        except Exception as e:
            logger.error(f"포지션 종료 실패: {pos.symbol} - {str(e)}", exc_info=True)
            # 포지션은 Redis에서 제거하되 오류 기록
            self.redis.delete(self._get_position_key(pos.symbol))
            raise OrderServiceException(f"포지션 종료 실패: {str(e)}")

    async def _update_trailing_stop(self, pos: PositionData, price: float):
        """동적 손절 로직을 업데이트합니다."""
        key = self._get_position_key(pos.symbol)
        updated = False
        
        # 트레일링 스탑 활성화 조건 확인
        if not pos.trailing_stop_activated:
            if self._should_activate_trailing_stop(pos, price):
                self.redis.hset(key, "trailing_stop_activated", "True")
                logger.info(f"트레일링 스탑 활성화", symbol=pos.symbol)
                updated = True

        # 트레일링 스탑이 활성화된 경우 손절선 업데이트
        if pos.trailing_stop_activated or updated:
            new_stop_loss = self._calculate_new_stop_loss(pos, price)
            if self._should_update_stop_loss(pos, new_stop_loss):
                self.redis.hset(key, "current_stop_loss", str(new_stop_loss))
                
                # 최고가/최저가 업데이트
                if pos.side == TRADING["SIDES"]["LONG"]:
                    highest = max(pos.highest_price_so_far, price)
                    self.redis.hset(key, "highest_price_so_far", str(highest))
                else:
                    lowest = min(pos.lowest_price_so_far, price)
                    self.redis.hset(key, "lowest_price_so_far", str(lowest))
                
                logger.info(
                    f"손절선 업데이트: {new_stop_loss:.4f}",
                    symbol=pos.symbol,
                    side=pos.side,
                    old_stop_loss=pos.current_stop_loss,
                    new_stop_loss=new_stop_loss
                )

    def _should_activate_trailing_stop(self, pos: PositionData, price: float) -> bool:
        """트레일링 스탑 활성화 조건을 확인합니다."""
        activation_price_long = pos.entry_price + (pos.initial_risk_distance * self.settings.TP_RATIO)
        activation_price_short = pos.entry_price - (pos.initial_risk_distance * self.settings.TP_RATIO)
        
        return (pos.side == TRADING["SIDES"]["LONG"] and price >= activation_price_long) or \
               (pos.side == TRADING["SIDES"]["SHORT"] and price <= activation_price_short)

    def _calculate_new_stop_loss(self, pos: PositionData, price: float) -> float:
        """새로운 손절선을 계산합니다."""
        atr_val = pos.initial_risk_distance
        
        if pos.side == TRADING["SIDES"]["LONG"]:
            highest = max(pos.highest_price_so_far, price)
            return highest - (atr_val * self.settings.ATR_MULTIPLIER)
        else:
            lowest = min(pos.lowest_price_so_far, price)
            return lowest + (atr_val * self.settings.ATR_MULTIPLIER)

    def _should_update_stop_loss(self, pos: PositionData, new_stop_loss: float) -> bool:
        """손절선 업데이트 여부를 결정합니다."""
        if pos.side == TRADING["SIDES"]["LONG"]:
            return new_stop_loss > pos.current_stop_loss
        else:
            return new_stop_loss < pos.current_stop_loss

    async def close_position_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """특정 심볼의 포지션을 수동으로 종료합니다."""
        position = self.get_position(symbol)
        if not position:
            raise PositionException(f"포지션이 존재하지 않습니다: {symbol}")
        
        # 현재 가격 조회
        current_price = await self.binance_adapter.get_latest_price(symbol)
        
        # 포지션 종료
        await self._close_position(position, current_price, TRADING["CLOSE_REASONS"]["MANUAL_CLOSE"])
        
        return create_api_response(
            success=True,
            data={
                "symbol": symbol,
                "close_price": current_price,
                "profit_loss": position.calculate_profit_loss(current_price),
                "reason": TRADING["CLOSE_REASONS"]["MANUAL_CLOSE"]
            },
            message="포지션이 성공적으로 종료되었습니다."
        )

    @timeout(timeout_seconds=300)
    async def close_all_positions(self) -> Dict[str, Any]:
        """모든 포지션을 종료합니다."""
        symbols = self.get_all_position_symbols()
        results = []
        
        for symbol in symbols:
            try:
                result = await self.close_position_by_symbol(symbol)
                results.append(result)
            except Exception as e:
                logger.error(f"포지션 종료 실패", symbol=symbol, error=str(e))
                results.append(create_api_response(
                    success=False,
                    data={"symbol": symbol},
                    message=f"포지션 종료 실패: {str(e)}"
                ))
        
        return create_api_response(
            success=True,
            data={"results": results},
            message=f"총 {len(results)}개 포지션 종료 처리 완료"
        )

    def get_position_summary(self) -> Dict[str, Any]:
        """포지션 요약 정보를 반환합니다."""
        positions = self.get_all_positions()
        
        if not positions:
            return create_api_response(
                success=True,
                data={"total_positions": 0, "positions": []},
                message="활성 포지션이 없습니다."
            )
        
        summary = {
            "total_positions": len(positions),
            "long_positions": sum(1 for p in positions if p.side == TRADING["SIDES"]["LONG"]),
            "short_positions": sum(1 for p in positions if p.side == TRADING["SIDES"]["SHORT"]),
            "total_unrealized_pnl": 0.0,
            "positions": []
        }
        
        for position in positions:
            # 현재 가격 조회 (비동기 처리 필요시 별도 메서드로 분리)
            current_price = None
            try:
                # 임시로 Redis에서 마지막 가격 조회
                price_key = f"{REDIS_KEYS['PRICE_PREFIX']}{position.symbol}"
                current_price = self.redis.get(price_key)
                current_price = float(current_price) if current_price else position.entry_price
            except:
                current_price = position.entry_price
            
            pnl = position.calculate_profit_loss(current_price)
            summary["total_unrealized_pnl"] += pnl
            
            position_info = {
                "symbol": position.symbol,
                "side": position.side,
                "entry_price": position.entry_price,
                "current_price": current_price,
                "current_stop_loss": position.current_stop_loss,
                "unrealized_pnl": pnl,
                "pnl_percentage": position.get_unrealized_pnl_percentage(current_price),
                "entry_timestamp": position.entry_timestamp.isoformat(),
                "trailing_stop_activated": position.trailing_stop_activated
            }
            summary["positions"].append(position_info)
        
        return create_api_response(
            success=True,
            data=summary,
            message="포지션 요약 정보 조회 완료"
        )

    def get_trading_status(self) -> Dict[str, Any]:
        """거래 상태 정보를 반환합니다."""
        return create_api_response(
            success=True,
            data={
                "auto_trading_enabled": self.settings.AUTO_TRADING_ENABLED,
                "active_positions": len(self.get_all_positions()),
                "max_positions": DEFAULTS["MAX_POSITIONS"],
                "can_create_new_position": len(self.get_all_positions()) < DEFAULTS["MAX_POSITIONS"],
                "monitoring_active": True  # 모니터링은 항상 활성
            },
            message="거래 상태 조회 완료"
        )

    def toggle_auto_trading(self) -> Dict[str, Any]:
        """자동 거래 활성화/비활성화를 토글합니다."""
        self.settings.AUTO_TRADING_ENABLED = not self.settings.AUTO_TRADING_ENABLED
        self.redis.hset(REDIS_KEYS["TRADING_SETTINGS"], "AUTO_TRADING_ENABLED", str(self.settings.AUTO_TRADING_ENABLED))
        
        status = "활성화" if self.settings.AUTO_TRADING_ENABLED else "비활성화"
        logger.info(f"자동 거래 {status}")
        
        return create_api_response(
            success=True,
            data={"auto_trading_enabled": self.settings.AUTO_TRADING_ENABLED},
            message=f"자동 거래가 {status}되었습니다."
        )
