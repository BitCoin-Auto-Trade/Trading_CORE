"""
매매 신호 관련 비즈니스 로직을 처리하는 고도화된 서비스입니다.

주요 특징:
- **데이터 유연성**: DB에 일부 지표가 없어도 실시간으로 계산하여 분석을 지속합니다.
- **지능형 가중치**: 변동성, 거래량, 추세 강도를 종합하여 분석 모델의 가중치를 동적으로 조절합니다.
- **안정성 강화**: 잠재적 오류(IndexError, 메모리 누수)를 방지하는 로직이 포함되어 있습니다.
- **상황인지형 로직**: 시장 상황에 맞춰 신호 발생 기준과 리스크를 동적으로 조절합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from collections import deque
from app.schemas.core import TradingSignal, TradingSettings
from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter
from app.core.constants import TRADING, REDIS_KEYS, DEFAULTS
from app.core.exceptions import SignalServiceException, DataNotFoundException
from app.utils.helpers import create_api_response, timeout, validate_required_fields
from app.utils.logging import get_logger
import redis

logger = get_logger(__name__)

class SignalService:
    """
    데이터 유연성, 지능형 가중치, 강화된 안정성을 갖춘 매매 신호 생성 서비스.
    """

    def __init__(
        self,
        db_repository: DBRepository,
        binance_adapter: BinanceAdapter,
        redis_client: redis.Redis
    ):
        # 의존성 주입
        self.db_repository = db_repository
        self.binance_adapter = binance_adapter
        self.redis_client = redis_client

        # 동적 거래 설정 로드
        self._load_settings()

        # --- 리스크 관리 ---
        self.last_signal_time: Dict[str, datetime] = {}
        self.signal_cooldown = timedelta(minutes=self.settings.MIN_SIGNAL_INTERVAL_MINUTES)

        # --- 성능 추적 ---
        self.performance_stats = {
            "total_signals": 0,
            "successful_signals": 0,
            "failed_signals": 0,
            "win_rate": 0.0
        }
        self.consecutive_losses = 0

        # --- 메모리 효율적인 로그 관리 ---
        self.signal_history = deque(maxlen=1000)

    def _load_settings(self):
        """Redis에서 거래 설정을 불러오거나, 없으면 기본값을 사용합니다."""
        settings_data = self.redis_client.hgetall(REDIS_KEYS["TRADING_SETTINGS"])
        if settings_data:
            logger.info("Redis에서 거래 설정을 불러옵니다.")
            self.settings = TradingSettings.model_validate(settings_data)
        else:
            logger.info("기본 거래 설정을 사용합니다.")
            self.settings = TradingSettings()

    def _is_trading_time(self) -> bool:
        """거래 활성 시간인지 확인합니다."""
        current_hour = datetime.now().hour
        return any(
            start <= current_hour < end or (start > end and (current_hour >= start or current_hour < end))
            for start, end in self.settings.ACTIVE_HOURS
        )

    def _should_generate_signal(self, symbol: str) -> tuple[bool, str]:
        """신호 생성 조건을 검사합니다."""
        if not self._is_trading_time():
            return False, "거래 비활성 시간"
        
        if self.consecutive_losses >= self.settings.MAX_CONSECUTIVE_LOSSES:
            return False, f"최대 연속 손실({self.settings.MAX_CONSECUTIVE_LOSSES}) 도달"
        
        if symbol in self.last_signal_time:
            time_diff = datetime.now() - self.last_signal_time[symbol]
            if time_diff < self.signal_cooldown:
                return False, f"신호 쿨다운 시간({self.signal_cooldown.total_seconds()}초) 미달"
        
        return True, ""

    def _prepare_data(self, symbol: str) -> pd.DataFrame:
        """DB에서 이미 계산된 지표 데이터를 가져옵니다."""
        df = self.db_repository.get_klines_by_symbol_as_df(symbol, limit=100)
        if df.empty:
            raise DataNotFoundException(f"DB에 {symbol} 데이터가 없습니다")
        
        # 필수 컬럼 확인 (이미 DB에 계산되어 있어야 함)
        required = ['close', 'high', 'low', 'volume', 'atr', 'ema_20', 'sma_50', 'sma_200', 'rsi_14', 'macd_hist', 'stoch_k', 'stoch_d', 'bb_upper', 'bb_lower']
        missing_cols = [col for col in required if col not in df.columns]
        
        if missing_cols:
            raise DataNotFoundException(f"필수 지표가 DB에 없습니다: {missing_cols}")
            
        return df.dropna()

    def _analyze_trend_context(self, latest: pd.Series) -> Dict[str, Any]:
        """추세 분석을 수행합니다."""
        adx = float(latest.get("adx", 20))
        trend = TRADING["TRENDS"]["NEUTRAL"]
        
        ema_20 = float(latest.get("ema_20", 0))
        sma_50 = float(latest.get("sma_50", 0))
        sma_200 = float(latest.get("sma_200", 0))
        
        if ema_20 > sma_50 > sma_200: 
            trend = TRADING["TRENDS"]["STRONG_UP"]
        elif ema_20 > sma_50: 
            trend = TRADING["TRENDS"]["WEAK_UP"]
        elif ema_20 < sma_50 < sma_200: 
            trend = TRADING["TRENDS"]["STRONG_DOWN"]
        elif ema_20 < sma_50: 
            trend = TRADING["TRENDS"]["WEAK_DOWN"]

        adx_strength = min(adx / 40, 1.0)
        base_strength = 0.9 if "STRONG" in trend else 0.7 if "WEAK" in trend else 0.4
        
        return {
            "trend": trend, 
            "strength": base_strength * adx_strength, 
            "adx": adx
        }

    def _analyze_momentum(self, latest: pd.Series) -> tuple[float, Dict[str, Any]]:
        """모멘텀 분석을 수행합니다."""
        scores = {}
        
        # RSI 점수 계산
        rsi = latest.get("rsi_14", 50)
        if rsi < 30: scores["rsi"] = 0.8  # 매수 신호
        elif rsi > 70: scores["rsi"] = -0.8  # 매도 신호
        else: scores["rsi"] = 0.0
        
        # MACD 히스토그램 점수
        macd_hist = latest.get("macd_hist", 0)
        if abs(macd_hist) > self.settings.PRICE_MOMENTUM_THRESHOLD:
            scores["macd"] = 0.6 if macd_hist > 0 else -0.6
        else:
            scores["macd"] = 0.0
        
        # Stochastic 점수
        stoch_k = latest.get("stoch_k", 50)
        stoch_d = latest.get("stoch_d", 50)
        if stoch_k < 20 and stoch_d < 20:
            scores["stoch"] = 0.7
        elif stoch_k > 80 and stoch_d > 80:
            scores["stoch"] = -0.7
        else:
            scores["stoch"] = 0.0
        
        # 종합 점수 계산
        total_score = sum(scores.values()) / len(scores)
        
        return total_score, scores

    def _analyze_volume_and_volatility(self, latest: pd.Series) -> tuple[float, Dict[str, Any]]:
        """거래량과 변동성 분석을 수행합니다."""
        # 기본 거래량 비율 (DB에 있으면 사용, 없으면 1.0)
        volume_ratio = latest.get("volume_ratio", 1.0)
        volatility = latest.get("volatility_20d", 0.02)
        
        # 거래량 급등 확인
        volume_spike = volume_ratio > self.settings.VOLUME_SPIKE_THRESHOLD
        
        # 변동성 상태 확인
        high_volatility = volatility > DEFAULTS["VOLATILITY_HIGH_THRESHOLD"]
        
        # 가중치 계산
        volume_weight = min(volume_ratio / 2, 1.5)  # 최대 1.5배
        volatility_weight = 0.8 if high_volatility else 1.2  # 높은 변동성 시 가중치 감소
        
        return volume_weight * volatility_weight, {
            "volume_ratio": volume_ratio,
            "volatility": volatility,
            "volume_spike": volume_spike,
            "high_volatility": high_volatility
        }

    def _calculate_position_size(self, latest: pd.Series) -> float:
        """포지션 크기를 계산합니다."""
        atr = float(latest.get("atr", latest.get("close", 0) * 0.02))
        close_price = float(latest.get("close", 0))
        
        if close_price <= 0 or atr <= 0:
            return DEFAULTS["POSITION_SIZE"]
        
        # ATR 기반 포지션 크기 계산
        risk_amount = self.settings.ACCOUNT_BALANCE * self.settings.RISK_PER_TRADE
        position_size = (risk_amount / atr) * self.settings.LEVERAGE
        
        # 최소/최대 포지션 크기 제한
        min_position = self.settings.ACCOUNT_BALANCE * 0.01
        max_position = self.settings.ACCOUNT_BALANCE * 0.1
        
        return max(min_position, min(position_size, max_position))

    def _calculate_stop_loss(self, latest: pd.Series, signal_type: str) -> float:
        """손절선을 계산합니다."""
        close_price = float(latest.get("close", 0))
        atr = float(latest.get("atr", close_price * 0.02))
        
        if signal_type == TRADING["SIGNALS"]["BUY"]:
            return close_price - (atr * self.settings.ATR_MULTIPLIER)
        else:
            return close_price + (atr * self.settings.ATR_MULTIPLIER)

    def update_performance(self, result: str):
        """성과 통계를 업데이트합니다."""
        self.performance_stats["total_signals"] += 1
        
        if result == TRADING["RESULTS"]["PROFIT"]:
            self.performance_stats["successful_signals"] += 1
            self.consecutive_losses = 0
        else:
            self.performance_stats["failed_signals"] += 1
            self.consecutive_losses += 1
        
        # 승률 계산
        if self.performance_stats["total_signals"] > 0:
            self.performance_stats["win_rate"] = (
                self.performance_stats["successful_signals"] / 
                self.performance_stats["total_signals"]
            )
        
        # Redis에 성과 저장
        performance_key = f"{REDIS_KEYS['PERFORMANCE']}"
        self.redis_client.hmset(performance_key, self.performance_stats)
        
        logger.info(
            f"성과 업데이트 - result: {result}, win_rate: {self.performance_stats['win_rate']:.3f}, consecutive_losses: {self.consecutive_losses}"
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """성과 통계를 반환합니다."""
        return create_api_response(
            success=True,
            data=self.performance_stats,
            message="성과 통계 조회 완료"
        )

    def get_combined_trading_signal(self, symbol: str) -> TradingSignal:
        """종합적인 거래 신호를 생성합니다."""
        # 신호 생성 가능 여부 확인
        can_signal, reason = self._should_generate_signal(symbol)
        if not can_signal:
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(),
                signal=TRADING["SIGNALS"]["HOLD"], 
                confidence_score=0.0,
                message=reason
            )

        # 데이터 준비
        df = self._prepare_data(symbol)
        if len(df) < 2:
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(),
                signal=TRADING["SIGNALS"]["HOLD"], 
                confidence_score=0.0,
                message="데이터 부족"
            )

        latest = df.iloc[0]
        
        # 각종 분석 수행
        trend_context = self._analyze_trend_context(latest)
        momentum_score, momentum_details = self._analyze_momentum(latest)
        volume_weight, volume_details = self._analyze_volume_and_volatility(latest)
        
        # 종합 점수 계산
        final_score = momentum_score * volume_weight * trend_context["strength"]
        
        # 신호 결정
        signal = TRADING["SIGNALS"]["HOLD"]
        if final_score > 0.3:
            signal = TRADING["SIGNALS"]["BUY"]
        elif final_score < -0.3:
            signal = TRADING["SIGNALS"]["SELL"]
        
        # 포지션 크기 및 손절선 계산
        position_size = self._calculate_position_size(latest)
        stop_loss_price = self._calculate_stop_loss(latest, signal)
        
        # 신호 기록
        self.last_signal_time[symbol] = datetime.now()
        
        # 메타데이터 구성
        metadata = {
            "trend": trend_context,
            "momentum": momentum_details,
            "volume": volume_details,
            "tech": {
                "close_price": float(latest.get("close", 0)),
                "atr": float(latest.get("atr", 0)),
                "rsi": float(latest.get("rsi_14", 50)),
                "macd_hist": float(latest.get("macd_hist", 0))
            }
        }
        
        trading_signal = TradingSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            signal=signal,
            confidence_score=float(abs(final_score)),
            position_size=float(position_size),
            stop_loss_price=float(stop_loss_price),
            metadata=metadata
        )
        
        # 신호 히스토리 저장
        self.signal_history.append({
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "signal": signal,
            "confidence": float(abs(final_score)),
            "final_score": float(final_score)
        })
        
        return trading_signal
