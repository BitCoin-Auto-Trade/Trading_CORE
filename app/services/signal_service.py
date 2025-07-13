"""
매매 신호 관련 비즈니스 로직을 처리합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
from app.schemas.core import TradingSignal
from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter


class SignalService:
    """
    다양한 지표와 시장 상황을 종합하여 매매 신호를 생성하는 서비스 클래스.
    """

    def __init__(self, db_repository: DBRepository, binance_adapter: BinanceAdapter):
        self.db_repository = db_repository
        self.binance_adapter = binance_adapter

        # --- 기본 거래 설정 ---
        self.timeframe = "1m"  # 분석에 사용할 시간봉
        self.leverage = 10  # 레버리지
        self.risk_per_trade = 0.02  # 거래당 리스크 비율 (계좌 잔고 대비)
        self.account_balance = 10000  # 초기 계좌 잔고 (TODO: 실제 잔고와 연동 필요)

        # --- 손절 및 익절 설정 ---
        self.atr_multiplier = 1.5  # 손절 계산 시 사용할 ATR 배수
        self.tp_ratio = 1.5  # 익절 비율 (손절 대비)

        # --- 단타(Scalping) 특화 임계값 ---
        self.volume_spike_threshold = 2.0  # 거래량 급증 판단 기준 (이동평균 대비)
        self.price_momentum_threshold = 0.003  # 가격 모멘텀 판단 기준

        # --- 리스크 관리 설정 ---
        self.last_signal_time: Dict[str, datetime] = {}  # 심볼별 마지막 신호 발생 시간
        self.min_signal_interval = timedelta(minutes=5)  # 최소 신호 발생 간격
        self.consecutive_losses = 0  # 연속 손실 횟수
        self.max_consecutive_losses = 3  # 최대 연속 손실 허용 횟수
        self.active_hours = [(9, 24), (0, 2)]  # 거래 활성 시간 (한국 시간 기준)

        # --- 백테스팅용 로그 ---
        self.signal_history = []  # 생성된 신호 기록

    def _is_trading_time(self) -> bool:
        """현재 시간이 거래 가능한 시간인지 확인합니다."""
        current_hour = datetime.now().hour
        # active_hours에 정의된 시간 범위에 현재 시간이 포함되는지 확인
        return any(
            start <= current_hour < end
            or (start > end and (current_hour >= start or current_hour < end))
            for start, end in self.active_hours
        )

    def _should_generate_signal(self, symbol: str) -> tuple[bool, str]:
        """새로운 매매 신호를 생성할 수 있는 조건인지 확인합니다."""
        if not self._is_trading_time():
            return False, "거래 비활성 시간입니다."
        if self.consecutive_losses >= self.max_consecutive_losses:
            return (
                False,
                f"최대 연속 손실 횟수({self.max_consecutive_losses})에 도달했습니다.",
            )
        if (
            symbol in self.last_signal_time
            and datetime.now() - self.last_signal_time[symbol]
            < self.min_signal_interval
        ):
            return (
                False,
                f"최소 신호 발생 간격({self.min_signal_interval.total_seconds()}초)이 지나지 않았습니다.",
            )
        return True, ""

    def _prepare_data_with_indicators(self, symbol: str) -> pd.DataFrame:
        """DB에서 K-line 데이터와 미리 계산된 지표를 가져와 데이터프레임을 준비합니다."""
        df = self.db_repository.get_klines_by_symbol_as_df(symbol, limit=500)
        if df.empty:
            return pd.DataFrame()

        # --- 추가 지표 계산 ---
        df["volume_sma"] = df["volume"].rolling(20).mean()  # 거래량 이동평균
        df["volume_ratio"] = df["volume"] / df["volume_sma"]  # 거래량 비율
        df["price_momentum"] = df["close"].pct_change(5)  # 가격 변화율 (모멘텀)
        df["volatility"] = (
            df["high"].rolling(20).std() / df["close"].rolling(20).mean()
        )  # 변동성

        return df # 최신 데이터가 위로 오도록 정렬된 상태로 받음


    def _analyze_trend_context(self, df: pd.DataFrame) -> Dict:
        """이동평균선을 기반으로 현재 추세를 분석합니다."""
        if len(df) < 50:
            return {"trend": "UNKNOWN", "strength": 0}

        latest = df.iloc[0]
        trend = "NEUTRAL"
        # EMA 정배열/역배열 상태로 추세 판단
        if latest["ema_20"] > latest["sma_50"] > latest["sma_200"]:
            trend = "STRONG_UP"
        elif latest["ema_20"] > latest["sma_50"]:
            trend = "WEAK_UP"
        elif latest["ema_20"] < latest["sma_50"] < latest["sma_200"]:
            trend = "STRONG_DOWN"
        elif latest["ema_20"] < latest["sma_50"]:
            trend = "WEAK_DOWN"

        strength = 0.9 if "STRONG" in trend else 0.7 if "WEAK" in trend else 0.5
        return {"trend": trend, "strength": strength, "adx": latest.get("adx", 20)}

    def _analyze_momentum(
        self, df: pd.DataFrame, trend_context: Dict
    ) -> tuple[str, float, dict]:
        """가격 및 거래량 모멘텀을 분석하여 신호와 점수를 반환합니다."""
        if len(df) < 50:
            return "HOLD", 0, {}

        latest = df.iloc[0]
        scores = []
        momentum = latest["price_momentum"]
        volatility = latest["volatility"]
        normalized_momentum = momentum / max(
            volatility, 0.0001
        )  # 변동성으로 정규화된 모멘텀

        # EMA 크로스오버
        if latest["ema_20"] > latest["sma_50"]:
            scores.append(1.0)
        elif latest["ema_20"] < latest["sma_50"]:
            scores.append(-1.0)

        # 정규화된 모멘텀
        if normalized_momentum > 1.5:
            scores.append(1.5)
        elif normalized_momentum < -1.5:
            scores.append(-1.5)

        # 거래량 급증
        if latest["volume_ratio"] > self.volume_spike_threshold:
            score = 1.0 if momentum > 0 else -1.0
            # 추세와 같은 방향일 때 가중치 부여
            if (score > 0 and "UP" in trend_context["trend"]) or (
                score < 0 and "DOWN" in trend_context["trend"]
            ):
                scores.append(score)
            else:
                scores.append(score * 0.5)  # 추세와 반대 방향일 때 가중치 감소

        total_score = sum(scores)
        info = {
            "normalized_momentum": normalized_momentum,
            "volume_ratio": latest["volume_ratio"],
        }
        signal = "BUY" if total_score > 1 else "SELL" if total_score < -1 else "HOLD"
        return signal, total_score, info

    def _analyze_technical_indicators(
        self, df: pd.DataFrame, trend_context: Dict
    ) -> tuple[str, float, dict]:
        """RSI, MACD, Stochastic 등 기술적 지표를 분석하여 신호와 점수를 반환합니다."""
        if len(df) < 2:
            return "HOLD", 0, {}

        latest, previous = df.iloc[0], df.iloc[1]
        scores = []

        # RSI 과매수/과매도
        if latest["rsi_14"] <= 30:
            scores.append(1.0)
        elif latest["rsi_14"] >= 70:
            scores.append(-1.0)

        # MACD 골든크로스/데드크로스
        if (
            latest["macd"] > latest["macd_signal"]
            and previous["macd"] <= previous["macd_signal"]
        ):
            scores.append(1.5)
        elif (
            latest["macd"] < latest["macd_signal"]
            and previous["macd"] >= previous["macd_signal"]
        ):
            scores.append(-1.5)

        # Stochastic 과매수/과매도
        if latest.get("stoch_k", 50) <= 20:
            scores.append(0.8)
        elif latest.get("stoch_k", 50) >= 80:
            scores.append(-0.8)

        total_score = sum(scores)
        info = {
            "rsi": latest["rsi_14"],
            "macd": latest["macd"],
            "stoch_k": latest.get("stoch_k"),
        }
        signal = "BUY" if total_score > 1 else "SELL" if total_score < -1 else "HOLD"
        return signal, total_score, info

    def _analyze_orderbook(self, symbol: str) -> tuple[str, float, dict]:
        """실시간 오더북을 분석하여 매수/매도 압력을 판단합니다."""
        order_book = self.binance_adapter.get_order_book(symbol, limit=20)
        if not order_book or not order_book.get("bids") or not order_book.get("asks"):
            return "HOLD", 0, {}

        bids, asks = order_book["bids"][:10], order_book["asks"][:10]
        bid_volume = sum(float(bid[1]) for bid in bids)
        ask_volume = sum(float(ask[1]) for ask in asks)
        total_volume = bid_volume + ask_volume

        if total_volume == 0:
            return "HOLD", 0, {}

        bid_ratio = bid_volume / total_volume
        score = 0
        if bid_ratio > 0.65:  # 매수 압력이 강할 때
            score = 1.0
        elif bid_ratio < 0.35:  # 매도 압력이 강할 때
            score = -1.0

        info = {"bid_ratio": bid_ratio}
        signal = "BUY" if score > 0 else "SELL" if score < 0 else "HOLD"
        return signal, score, info

    def _calculate_position_size(self, current_price: float, stop_loss: float) -> float:
        """리스크 관리 원칙에 따라 적절한 포지션 크기를 계산합니다."""
        # 연속 손실에 따라 리스크 동적 조절
        risk_multiplier = max(0.3, 1.0 - (self.consecutive_losses * 0.2))
        adjusted_risk = self.risk_per_trade * risk_multiplier
        risk_amount = self.account_balance * adjusted_risk
        price_diff = abs(current_price - stop_loss)

        if price_diff == 0:
            return 0

        position_size = risk_amount / price_diff
        return round(position_size * self.leverage, 6)

    def _log_signal(self, log_data: Dict):
        """백테스팅 및 분석을 위해 생성된 신호 정보를 기록합니다."""
        self.signal_history.append({"timestamp": datetime.now(), **log_data})
        self.signal_history = self.signal_history[-1000:]  # 최근 1000개만 유지

    def get_combined_trading_signal(self, symbol: str) -> TradingSignal:
        """
        모든 분석 단계를 거쳐 최종 매매 신호를 생성합니다.
        """
        can_signal, reason = self._should_generate_signal(symbol)
        if not can_signal:
            return TradingSignal(
                symbol=symbol, signal="HOLD", message=f"거래 중단: {reason}"
            )

        df = self._prepare_data_with_indicators(symbol)
        if df.empty:
            return TradingSignal(
                symbol=symbol, signal="HOLD", message="데이터 부족으로 분석 불가"
            )

        latest = df.iloc[0]
        current_price = latest["close"]

        # --- 각 분석 모델 실행 ---
        trend_context = self._analyze_trend_context(df)
        m_sig, m_score, m_info = self._analyze_momentum(df, trend_context)
        t_sig, t_score, t_info = self._analyze_technical_indicators(df, trend_context)
        o_sig, o_score, o_info = self._analyze_orderbook(symbol)

        # --- 점수 가중 합산 ---
        trend_weight = trend_context["strength"]
        # 추세가 강할수록 모멘텀 가중치 증가, 기술적 지표 및 오더북 가중치 감소
        m_w, t_w, o_w = (
            0.4 + (0.2 * trend_weight),
            0.4 - (0.1 * trend_weight),
            0.2 - (0.1 * trend_weight),
        )
        final_score = (m_score * m_w) + (t_score * t_w) + (o_score * o_w)

        # --- 최종 신호 결정 ---
        if final_score >= 2.5:
            final_signal = "STRONG_BUY"
        elif final_score > 1.0:
            final_signal = "BUY"
        elif final_score <= -2.5:
            final_signal = "STRONG_SELL"
        elif final_score < -1.0:
            final_signal = "SELL"
        else:
            final_signal = "HOLD"

        sl_price, tp_price, pos_size = None, None, 0
        # 매수/매도 신호일 경우 손절/익절 가격 및 포지션 크기 계산
        if final_signal in ["STRONG_BUY", "BUY", "STRONG_SELL", "SELL"]:
            atr = latest.get("ATRr_14", current_price * 0.01)
            if "BUY" in final_signal:
                sl_price = current_price - atr * self.atr_multiplier
                tp_price = current_price + atr * self.atr_multiplier * self.tp_ratio
            else:  # SELL
                sl_price = current_price + atr * self.atr_multiplier
                tp_price = current_price - atr * self.atr_multiplier * self.tp_ratio

            pos_size = self._calculate_position_size(current_price, sl_price)
            self.last_signal_time[symbol] = datetime.now()

        self._log_signal(
            {
                "symbol": symbol,
                "signal": final_signal,
                "score": final_score,
                "trend": trend_context,
                "pos_size": pos_size,
            }
        )

        message = (
            f"하이브리드 신호: {final_signal} (점수: {final_score:.2f}) | "
            f"추세: {trend_context['trend']}(강도: {trend_context['strength']:.1f}) | "
            f"모멘텀({m_score:.1f}) | 기술적분석({t_score:.1f}) | 오더북({o_score:.1f}) | "
            f"포지션 크기: {pos_size:.4f} | 연속손실: {self.consecutive_losses}"
        )

        return TradingSignal(
            symbol=symbol,
            timestamp=latest.name,
            signal=final_signal,
            stop_loss_price=sl_price,
            take_profit_price=tp_price,
            position_size=pos_size,
            confidence_score=abs(final_score),
            message=message,
            metadata={
                "trend": trend_context,
                "momentum": m_info,
                "tech": t_info,
                "orderbook": o_info,
            },
        )

    def update_performance(self, result: str):
        """거래 결과에 따라 연속 손실 횟수를 업데이트합니다."""
        if result == "LOSS":
            self.consecutive_losses += 1
        elif result == "PROFIT":
            self.consecutive_losses = 0
