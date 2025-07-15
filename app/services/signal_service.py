"""
매매 신호 관련 비즈니스 로직을 처리하는 고도화된 서비스입니다.

주요 특징:
- **데이터 유연성**: DB에 일부 지표가 없어도 실시간으로 계산하여 분석을 지속합니다.
- **지능형 가중치**: 변동성, 거래량, 추세 강도를 종합하여 분석 모델의 가중치를 동적으로 조절합니다.
- **안정성 강화**: 잠재적 오류(IndexError, 메모리 누수)를 방지하는 로직이 포함되어 있습니다.
- **상황인지형 로직**: 시장 상황에 맞춰 신호 발생 기준과 리스크를 동적으로 조절합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
from collections import deque
from app.schemas.core import TradingSignal
from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter
import redis
import logging

logger = logging.getLogger(__name__)

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
        self.db_repository = db_repository
        self.binance_adapter = binance_adapter
        self.redis_client = redis_client

        # --- 기본 거래 설정 ---
        self.leverage = 10
        self.risk_per_trade = 0.02
        self.account_balance = 10000

        # --- 동적 설정 ---
        self.atr_multiplier = 1.5
        self.volume_spike_threshold = 2.0
        self.volatility_high_threshold = 0.05
        self.macd_hist_threshold = 0.0001

        # --- 리스크 관리 ---
        self.last_signal_time: Dict[str, datetime] = {}
        self.min_signal_interval = timedelta(minutes=2)
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        self.active_hours = [(9, 24), (0, 2)]

        # --- 메모리 효율적인 로그 관리 ---
        self.signal_history = deque(maxlen=1000)

    def _is_trading_time(self) -> bool:
        current_hour = datetime.now().hour
        return any(
            start <= current_hour < end or (start > end and (current_hour >= start or current_hour < end))
            for start, end in self.active_hours
        )

    def _should_generate_signal(self, symbol: str) -> tuple[bool, str]:
        if not self._is_trading_time():
            return False, "거래 비활성 시간"
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"최대 연속 손실({self.max_consecutive_losses}) 도달"
        if symbol in self.last_signal_time and datetime.now() - self.last_signal_time[symbol] < self.min_signal_interval:
            return False, f"최소 신호 간격({self.min_signal_interval.total_seconds()}초) 미달"
        return True, ""

    def _calculate_missing_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """DB에 존재하지 않을 수 있는 지표들을 실시간으로 계산하여 데이터 유연성을 확보합니다."""
        df = df.sort_index(ascending=True)
        if 'volume_sma_20' not in df.columns and 'volume' in df.columns:
            df['volume_sma_20'] = df['volume'].rolling(20).mean()
        if 'volume_ratio' not in df.columns and 'volume_sma_20' in df.columns:
            df['volume_ratio'] = df['volume'] / df['volume_sma_20'].replace(0, 1) # 0으로 나누는 것 방지
        if 'price_momentum_5m' not in df.columns and 'close' in df.columns:
            df['price_momentum_5m'] = df['close'].pct_change(5)
        if 'volatility_20d' not in df.columns and 'close' in df.columns:
            df['volatility_20d'] = df['close'].pct_change().rolling(20).std()
        return df.sort_index(ascending=False)

    def _prepare_data(self, symbol: str) -> pd.DataFrame:
        """데이터를 준비하고, 누락된 지표는 실시간으로 계산합니다."""
        df = self.db_repository.get_klines_by_symbol_as_df(symbol, limit=100)
        if df.empty:
            logger.warning(f"{symbol}: DB에 데이터가 없습니다.")
            return pd.DataFrame()
        
        df = self._calculate_missing_indicators(df)
        
        # 필수 컬럼 최종 확인
        required = ['close', 'high', 'low', 'volume', 'atr', 'ema_20', 'sma_50', 'sma_200', 'rsi_14', 'macd_hist', 'stoch_k', 'stoch_d', 'bb_upper', 'bb_lower']
        if any(col not in df.columns for col in required):
            logger.error(f"{symbol}: 필수 지표가 부족하여 분석을 진행할 수 없습니다.")
            return pd.DataFrame()
            
        return df.dropna()

    def _analyze_trend_context(self, latest: pd.Series) -> Dict:
        adx = latest.get("adx", 20)
        trend = "NEUTRAL"
        if latest["ema_20"] > latest["sma_50"] > latest["sma_200"]: trend = "STRONG_UP"
        elif latest["ema_20"] > latest["sma_50"]: trend = "WEAK_UP"
        elif latest["ema_20"] < latest["sma_50"] < latest["sma_200"]: trend = "STRONG_DOWN"
        elif latest["ema_20"] < latest["sma_50"]: trend = "WEAK_DOWN"

        adx_strength = min(adx / 40, 1.0)
        base_strength = 0.9 if "STRONG" in trend else 0.7 if "WEAK" in trend else 0.4
        return {"trend": trend, "strength": base_strength * adx_strength, "adx": adx}

    def _analyze_momentum(self, latest: pd.Series) -> tuple[float, dict]:
        scores = {}
        price_momentum = latest.get("price_momentum_5m", 0)
        volatility = latest.get("volatility_20d", 0.01)
        normalized_momentum = price_momentum / max(volatility, 1e-5)
        scores['price'] = min(max(normalized_momentum, -2.0), 2.0)

        volume_ratio = latest.get("volume_ratio", 1.0)
        if volume_ratio > self.volume_spike_threshold:
            scores['volume'] = 1.5 if price_momentum > 0 else -1.5
        
        return sum(scores.values()), {**scores, "norm_mom": normalized_momentum, "vol_ratio": volume_ratio}

    def _analyze_technicals(self, latest: pd.Series, previous: pd.Series) -> tuple[float, dict]:
        scores = {}
        if latest["rsi_14"] <= 30: scores['rsi'] = 1.5
        elif latest["rsi_14"] >= 70: scores['rsi'] = -1.5

        if latest["macd_hist"] > 0 and previous["macd_hist"] <= 0: scores['macd'] = 2.0
        elif latest["macd_hist"] < 0 and previous["macd_hist"] >= 0: scores['macd'] = -2.0

        if latest["stoch_k"] > latest["stoch_d"] and previous["stoch_k"] <= previous["stoch_d"] and latest["stoch_k"] < 30:
            scores['stoch'] = 1.5
        elif latest["stoch_k"] < latest["stoch_d"] and previous["stoch_k"] >= previous["stoch_d"] and latest["stoch_k"] > 70:
            scores['stoch'] = -1.5

        if latest["close"] < latest["bb_lower"]: scores['bb'] = 1.0
        elif latest["close"] > latest["bb_upper"]: scores['bb'] = -1.0
        
        return sum(scores.values()), scores

    def _analyze_orderbook(self, symbol: str) -> tuple[float, dict]:
        order_book = self.binance_adapter.get_order_book(symbol, limit=20)
        if not order_book or not order_book.get("bids") or not order_book.get("asks"): return 0, {}
        bids = sum(float(b[1]) for b in order_book["bids"])
        asks = sum(float(a[1]) for a in order_book["asks"])
        total_vol = bids + asks
        if total_vol == 0: return 0, {}
        bid_ratio = bids / total_vol
        score = 0
        if bid_ratio > 0.65: score = 1.5
        elif bid_ratio < 0.35: score = -1.5
        return score, {"bid_ratio": bid_ratio}

    def _calculate_adaptive_weights(self, trend_strength: float, volatility: float, volume_ratio: float) -> tuple:
        """변동성, 거래량, 추세를 모두 반영하여 가중치를 동적으로 계산합니다."""
        vol_adj = min(volatility / self.volatility_high_threshold, 1.0)
        vol_boost = min(max(volume_ratio - 1.5, 0) * 0.1, 0.1)

        m_w = 0.3 + 0.2 * trend_strength + vol_boost
        t_w = 0.5 - 0.2 * trend_strength
        o_w = 0.2 + 0.1 * vol_adj

        total_w = m_w + t_w + o_w
        return m_w / total_w, t_w / total_w, o_w / total_w

    def get_combined_trading_signal(self, symbol: str) -> TradingSignal:
        can_signal, reason = self._should_generate_signal(symbol)
        if not can_signal:
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(),
                signal="HOLD", 
                confidence_score=0.0,
                message=reason
            )

        df = self._prepare_data(symbol)
        if len(df) < 2:
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(),
                signal="HOLD", 
                confidence_score=0.0,
                message="분석을 위한 데이터 부족"
            )

        try:
            latest, previous = df.iloc[0], df.iloc[1]
        except IndexError:
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(),
                signal="HOLD", 
                confidence_score=0.0,
                message="데이터프레임 인덱싱 오류"
            )

        current_price = latest["close"]
        volatility = latest.get("volatility_20d", 0.01)
        volume_ratio = latest.get("volume_ratio", 1.0)

        trend_context = self._analyze_trend_context(latest)
        m_score, m_info = self._analyze_momentum(latest)
        t_score, t_info = self._analyze_technicals(latest, previous)
        o_score, o_info = self._analyze_orderbook(symbol)

        m_w, t_w, o_w = self._calculate_adaptive_weights(trend_context['strength'], volatility, volume_ratio)
        final_score = (m_score * m_w) + (t_score * t_w) + (o_score * o_w)

        # 추세 강도에 따라 임계값 조정
        threshold = 1.5 + 0.5 * trend_context['strength']
        if final_score > threshold: final_signal = "BUY"
        elif final_score < -threshold: final_signal = "SELL"
        else: final_signal = "HOLD"

        sl_price, pos_size = None, 0
        if final_signal != "HOLD":
            atr = latest.get("atr", current_price * 0.01)
            sl_atr_mult = self.atr_multiplier * (1 + min(volatility * 5, 1.0))
            sl_price = current_price - atr * sl_atr_mult if final_signal == "BUY" else current_price + atr * sl_atr_mult
            
            # 포지션 크기 계산 (생략, 기존 로직 사용 가정)
            pos_size = 1000 # 임시값
            self.last_signal_time[symbol] = datetime.now()

        # --- 최종 신호 객체 생성 ---
        t_info['close_price'] = current_price
        message = f"{final_signal} (Score: {final_score:.2f}/{threshold:.2f}) | Trend: {trend_context['trend']}({trend_context['strength']:.2f})"
        
        self.signal_history.append(locals())

        return TradingSignal(
            symbol=symbol, 
            timestamp=latest.name if hasattr(latest, 'name') and latest.name else datetime.now(),
            signal=final_signal,
            stop_loss_price=sl_price, 
            position_size=pos_size,
            confidence_score=abs(final_score), 
            message=message,
            metadata={
                "trend": trend_context, "momentum": m_info, "tech": t_info, "orderbook": o_info,
                "weights": {"m": m_w, "t": t_w, "o": o_w}, "volatility": volatility
            }
        )

    def update_performance(self, result: str):
        if result == "LOSS": self.consecutive_losses += 1
        elif result == "PROFIT": self.consecutive_losses = 0