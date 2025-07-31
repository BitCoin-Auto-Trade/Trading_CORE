"""
트레이딩 신호 분석 및 생성 서비스

이 모듈은 다중 타임프레임 분석을 통해 신뢰성 높은 매매 신호를 생성합니다.

주요 기능:
- 다중 타임프레임 분석(Multi-Timeframe Analysis): 15분과 1분 차트를 동시 분석
- 동적 지표 가중치 조절: 시장 상황에 따른 적응형 신호 생성
- 리스크 관리: 연속 손실 및 신호 간격 제어
- 성능 추적: 신호 정확도 및 수익률 모니터링
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from collections import deque
from app.schemas.core import TradingSignal, TradingSettings
from app.repository.db_repository import DBRepository
from app.adapters.binance_adapter import BinanceAdapter
from app.core.constants import TRADING, REDIS_KEYS, DEFAULTS
from app.utils.redis_settings import parse_redis_settings
from app.core.exceptions import SignalServiceException, DataNotFoundException
from app.utils.helpers import create_api_response, timeout, validate_required_fields
from app.utils.logging import get_logger
import redis

logger = get_logger(__name__)

class TradingSignalAnalyzer:
    """트레이딩 신호 분석기
    
    다중 타임프레임 분석과 동적 가중치를 활용하여
    신뢰성 높은 매매 신호를 생성하는 핵심 서비스입니다.
    """

    def __init__(
        self,
        db_repository: DBRepository,
        binance_adapter: BinanceAdapter,
        redis_client: redis.Redis
    ):
        """신호 분석기 초기화
        
        Args:
            db_repository: 데이터베이스 저장소
            binance_adapter: 바이낸스 API 어댑터  
            redis_client: Redis 캐시 클라이언트
        """
        # 핵심 의존성 주입
        self.db_repository = db_repository
        self.binance_adapter = binance_adapter
        self.redis_client = redis_client

        # 거래 설정 초기화
        self._initialize_trading_settings()

        # 리스크 관리 매개변수
        self.last_signal_timestamps: Dict[str, datetime] = {}
        self.signal_cooldown_period = timedelta(minutes=self.settings.MIN_SIGNAL_INTERVAL_MINUTES)

        # 성능 추적 지표
        self.performance_metrics = {
            "total_signals_generated": 0,
            "successful_signals_count": 0,
            "failed_signals_count": 0,
            "current_win_rate": 0.0
        }
        self.consecutive_loss_count = 0

        # 메모리 효율적인 신호 이력 관리
        self.signal_history_buffer = deque(maxlen=1000)

    def _initialize_trading_settings(self) -> None:
        """거래 설정을 Redis에서 로드하거나 기본값으로 초기화"""
        try:
            settings_data = self.redis_client.hgetall(REDIS_KEYS["TRADING_SETTINGS"])
            if settings_data:
                logger.debug("Redis에서 거래 설정 로드 완료")
                parsed_settings = parse_redis_settings(settings_data)
                self.settings = TradingSettings.model_validate(parsed_settings)
            else:
                logger.debug("기본 거래 설정 사용")
                self.settings = TradingSettings()
        except Exception as e:
            logger.error(f"거래 설정 초기화 실패: {e}")
            self.settings = TradingSettings()

    def _is_within_trading_hours(self) -> bool:
        """현재 시간이 거래 활성 시간 범위에 포함되는지 확인
        
        Returns:
            거래 시간 여부
        """
        current_hour = datetime.now().hour
        return any(
            start <= current_hour < end or (start > end and (current_hour >= start or current_hour < end))
            for start, end in self.settings.ACTIVE_HOURS
        )

    def _validate_signal_generation_conditions(self, symbol: str) -> tuple[bool, str]:
        """신호 생성 가능 조건들을 종합적으로 검증
        
        Args:
            symbol: 검증할 거래 심볼
            
        Returns:
            (조건 만족 여부, 실패 사유)
        """
        # 거래 시간 확인
        if not self._is_within_trading_hours():
            return False, "거래 비활성 시간대"
        
        # 연속 손실 제한 확인
        if self.consecutive_loss_count >= self.settings.MAX_CONSECUTIVE_LOSSES:
            return False, f"최대 연속 손실({self.settings.MAX_CONSECUTIVE_LOSSES}) 한계 도달"
        
        # 신호 간격 제한 확인
        if symbol in self.last_signal_timestamps:
            time_elapsed = datetime.now() - self.last_signal_timestamps[symbol]
            if time_elapsed < self.signal_cooldown_period:
                remaining_seconds = (self.signal_cooldown_period - time_elapsed).total_seconds()
                return False, f"신호 쿨다운 대기 중 (남은 시간: {remaining_seconds:.0f}초)"
        
        return True, "조건 만족"

    def _load_market_data_with_cache(self, symbol: str, timeframe: str = "1m") -> pd.DataFrame:
        """캐시를 활용하여 시장 데이터를 효율적으로 로드
        
        Args:
            symbol: 거래 심볼
            timeframe: 시간 프레임 (기본값: 1분)
            
        Returns:
            기술적 지표가 포함된 시장 데이터 DataFrame
            
        Raises:
            DataNotFoundException: 필요한 데이터를 찾을 수 없는 경우
        """
        try:
            # Redis 캐시 키 생성
            cache_key = f"market_data:{symbol}:{timeframe}"
            
            # 캐시된 데이터 확인 및 복원 시도
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                try:
                    import pickle
                    df = pickle.loads(cached_data)
                    if not df.empty and len(df) >= 50:
                        logger.debug(f"캐시된 시장 데이터 사용: {symbol} ({timeframe})")
                        return df
                except Exception as cache_error:
                    logger.warning(f"캐시 데이터 복원 실패: {cache_error}")
            
            # 데이터베이스에서 신규 데이터 로드
            df = self.db_repository.get_klines_by_symbol_as_df(symbol, limit=200)
            if df.empty:
                raise DataNotFoundException(f"데이터베이스에 {symbol} ({timeframe}) 데이터가 존재하지 않음")
            
            # 컬럼명 매핑 (DB 컬럼명 -> 신호 분석용 컬럼명)
            column_mapping = {
                'open_price': 'open',
                'high_price': 'high', 
                'low_price': 'low',
                'close_price': 'close',
                'exponential_moving_average_20': 'ema_20',
                'simple_moving_average_50': 'sma_50',
                'simple_moving_average_200': 'sma_200',
                'relative_strength_index_14': 'rsi_14',
                'macd_line': 'macd',
                'macd_signal_line': 'macd_signal',
                'macd_histogram': 'macd_hist',
                'average_true_range': 'atr',
                'average_directional_index': 'adx',
                'bollinger_band_upper': 'bb_upper',
                'bollinger_band_middle': 'bb_middle',
                'bollinger_band_lower': 'bb_lower',
                'stochastic_k': 'stoch_k',
                'stochastic_d': 'stoch_d',
                'volume_simple_moving_average_20': 'volume_sma_20'
            }
            
            # 컬럼명 변경
            df = df.rename(columns=column_mapping)
            
            # 디버그: 매핑 후 컬럼명 확인
            logger.debug(f"매핑 후 컬럼명: {df.columns.tolist()}")
            
            # 필수 기술적 지표 컬럼 검증
            required_indicators = [
                'close', 'high', 'low', 'volume', 'atr', 'ema_20', 
                'sma_50', 'sma_200', 'rsi_14', 'macd_hist', 'stoch_k', 'stoch_d'
            ]
            missing_indicators = [col for col in required_indicators if col not in df.columns]
            
            if missing_indicators:
                logger.error(f"매핑 후에도 누락된 지표: {missing_indicators}")
                logger.error(f"실제 사용 가능한 컬럼: {df.columns.tolist()}")
                raise DataNotFoundException(f"필수 기술적 지표 누락: {missing_indicators}")
            
            # NaN 값 제거 후 유효성 검증
            df_cleaned = df.dropna()
            
            # 유효한 데이터를 캐시에 저장 (5분간 유지)
            if not df_cleaned.empty and len(df_cleaned) >= 50:
                try:
                    import pickle
                    self.redis_client.setex(cache_key, 300, pickle.dumps(df_cleaned))
                    logger.debug(f"시장 데이터 캐시 저장 완료: {symbol}")
                except Exception as cache_error:
                    logger.warning(f"데이터 캐시 저장 실패: {cache_error}")
            
            return df_cleaned
            
        except DataNotFoundException:
            raise
        except Exception as e:
            logger.error(f"시장 데이터 로드 중 예상치 못한 오류: {symbol} - {e}")
            raise DataNotFoundException(f"시장 데이터 로드 실패: {str(e)}")

    def _analyze_long_timeframe_trend(self, df_long: pd.DataFrame) -> Dict[str, Any]:
        """장기 타임프레임 추세 분석 수행
        
        Args:
            df_long: 장기 타임프레임 데이터 (15분봉)
            
        Returns:
            장기 추세 분석 결과
        """
        latest_candle = df_long.iloc[0]
        ema_20_value = float(latest_candle.get("ema_20", 0))
        sma_50_value = float(latest_candle.get("sma_50", 0))
        
        if ema_20_value > sma_50_value:
            trend = TRADING["TRENDS"]["WEAK_UP"]
        elif ema_20_value < sma_50_value:
            trend = TRADING["TRENDS"]["WEAK_DOWN"]
        else:
            trend = TRADING["TRENDS"]["NEUTRAL"]
            
        return {"trend": trend}

    def _analyze_short_timeframe_trend(self, latest_data: pd.Series) -> Dict[str, Any]:
        """단기 타임프레임 추세 분석 수행
        
        Args:
            latest_data: 최신 캔들 데이터
            
        Returns:
            단기 추세 분석 결과 
        """
        adx_value = float(latest_data.get("adx", 20))
        trend_direction = TRADING["TRENDS"]["NEUTRAL"]
        
        ema_20_value = float(latest_data.get("ema_20", 0))
        sma_50_value = float(latest_data.get("sma_50", 0))
        sma_200_value = float(latest_data.get("sma_200", 0))
        
        if ema_20_value > sma_50_value > sma_200_value: 
            trend_direction = TRADING["TRENDS"]["STRONG_UP"]
        elif ema_20_value > sma_50_value: 
            trend_direction = TRADING["TRENDS"]["WEAK_UP"]
        elif ema_20_value < sma_50_value < sma_200_value: 
            trend_direction = TRADING["TRENDS"]["STRONG_DOWN"]
        elif ema_20_value < sma_50_value: 
            trend_direction = TRADING["TRENDS"]["WEAK_DOWN"]

        # ADX 기반 추세 강도 계산 (0~1 정규화)
        adx_strength = min(adx_value / 40, 1.0)
        base_strength = 0.9 if "STRONG" in trend_direction else 0.7 if "WEAK" in trend_direction else 0.4
        
        return {
            "trend": trend_direction, 
            "strength": base_strength * adx_strength, 
            "adx": adx_value
        }

    def _calculate_momentum_score(self, market_data: pd.DataFrame, trend_context: Dict[str, Any]) -> tuple[float, Dict[str, Any]]:
        """동적 가중치와 임계값을 활용한 모멘텀 점수 계산
        
        Args:
            market_data: 시장 데이터 DataFrame
            trend_context: 추세 분석 컨텍스트
            
        Returns:
            (모멘텀 점수, 상세 분석 정보)
        """
        latest_data = market_data.iloc[0]
        scores = {}
        weights = {"rsi": 1.0, "macd": 1.0, "stoch": 1.0} # 기본 가중치

        # 추세에 따른 MACD, RSI/Stochastic 가중치 동적 조절
        trend = trend_context["trend"]
        if "UP" in trend or "DOWN" in trend:
            weights["macd"] = 1.5  # 추세장에서는 MACD 가중치 증가
            weights["rsi"] = 0.7
            weights["stoch"] = 0.7
        else: # 횡보장
            weights["macd"] = 0.7
            weights["rsi"] = 1.2 # 횡보장에서는 오실레이터 가중치 증가
            weights["stoch"] = 1.2

        # 동적 RSI 임계값 계산 (최근 50개 데이터의 표준편차 활용)
        rsi_std = market_data['rsi_14'].head(50).std()
        dynamic_upper_rsi = min(70, 50 + 2 * rsi_std)
        dynamic_lower_rsi = max(30, 50 - 2 * rsi_std)

        # RSI 점수 계산
        rsi_value = latest_data.get("rsi_14", 50)
        if rsi_value < dynamic_lower_rsi: 
            scores["rsi"] = 0.8
        elif rsi_value > dynamic_upper_rsi: 
            scores["rsi"] = -0.8
        else: 
            scores["rsi"] = 0.0
        
        # MACD 히스토그램 점수
        macd_hist_value = latest_data.get("macd_hist", 0)
        if abs(macd_hist_value) > self.settings.PRICE_MOMENTUM_THRESHOLD:
            scores["macd"] = 0.6 if macd_hist_value > 0 else -0.6
        else:
            scores["macd"] = 0.0
        
        # Stochastic 점수
        stoch_k_value = latest_data.get("stoch_k", 50)
        stoch_d_value = latest_data.get("stoch_d", 50)
        if stoch_k_value < 20 and stoch_d_value < 20:
            scores["stoch"] = 0.7
        elif stoch_k_value > 80 and stoch_d_value > 80:
            scores["stoch"] = -0.7
        else:
            scores["stoch"] = 0.0
        
        # 가중치 적용 종합 점수 계산
        weighted_score = sum(scores[k] * weights[k] for k in scores)
        total_weight = sum(weights.values())
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        
        details = {
            "scores": scores,
            "weights": weights,
            "dynamic_rsi_bounds": (dynamic_lower_rsi, dynamic_upper_rsi)
        }
        return final_score, details

    def _analyze_volume_and_volatility(self, latest_data: pd.Series) -> tuple[float, Dict[str, Any]]:
        """거래량 패턴과 변동성 수준 분석
        
        Args:
            latest_data: 최신 캔들 데이터
            
        Returns:
            (변동성 점수, 상세 분석 정보)
        """
        volume_ratio = latest_data.get("volume_ratio", 1.0)
        volatility_level = latest_data.get("volatility_20d", 0.02)
        
        is_volume_spike = volume_ratio > self.settings.VOLUME_SPIKE_THRESHOLD
        is_high_volatility = volatility_level > DEFAULTS["VOLATILITY_HIGH_THRESHOLD"]
        
        volume_weight = min(volume_ratio / 2, 1.5)
        volatility_weight = 0.8 if is_high_volatility else 1.2
        
        return volume_weight * volatility_weight, {
            "volume_ratio": volume_ratio,
            "volatility": volatility_level,
            "volume_spike": is_volume_spike,
            "high_volatility": is_high_volatility
        }

    def _calculate_optimal_position_size(self, latest_data: pd.Series) -> float:
        """ATR 기반 최적 포지션 크기 계산
        
        Args:
            latest_data: 최신 캔들 데이터
            
        Returns:
            계산된 포지션 크기
        """
        atr_value = float(latest_data.get("atr", latest_data.get("close", 0) * 0.02))
        current_price = float(latest_data.get("close", 0))
        
        if current_price <= 0 or atr_value <= 0:
            return DEFAULTS["POSITION_SIZE"]
        
        # 리스크 기반 포지션 크기 계산
        risk_amount = self.settings.ACCOUNT_BALANCE * self.settings.RISK_PER_TRADE
        position_size = (risk_amount / atr_value) * self.settings.LEVERAGE
        
        # 포지션 크기 제한 적용
        min_position = self.settings.ACCOUNT_BALANCE * 0.01
        max_position = self.settings.ACCOUNT_BALANCE * 0.1
        
        return max(min_position, min(position_size, max_position))

    def _calculate_stop_loss_level(self, latest_data: pd.Series, signal_direction: str) -> float:
        """ATR 기반 손절선 수준 계산
        
        Args:
            latest_data: 최신 캔들 데이터
            signal_direction: 신호 방향 ("BUY" 또는 "SELL")
            
        Returns:
            계산된 손절선 가격
        """
        current_price = float(latest_data.get("close", 0))
        atr_value = float(latest_data.get("atr", current_price * 0.02))
        
        if signal_direction == TRADING["SIGNALS"]["BUY"]:
            return current_price - (atr_value * self.settings.ATR_MULTIPLIER)
        else:
            return current_price + (atr_value * self.settings.ATR_MULTIPLIER)

    def update_trading_performance(self, trading_result: str) -> None:
        """거래 결과에 따른 성과 지표 업데이트
        
        Args:
            trading_result: 거래 결과 ("PROFIT" 또는 "LOSS")
        """
        self.performance_metrics["total_signals_generated"] += 1
        
        if trading_result == TRADING["RESULTS"]["PROFIT"]:
            self.performance_metrics["successful_signals_count"] += 1
            self.consecutive_loss_count = 0  # 성공 시 연속 손실 카운트 리셋
        else:
            self.performance_metrics["failed_signals_count"] += 1
            self.consecutive_loss_count += 1
        
        # 승률 계산 및 업데이트
        if self.performance_metrics["total_signals_generated"] > 0:
            self.performance_metrics["current_win_rate"] = (
                self.performance_metrics["successful_signals_count"] / 
                self.performance_metrics["total_signals_generated"]
            )
        
        # Redis에 성과 지표 저장
        performance_key = f"{REDIS_KEYS['PERFORMANCE']}"
        self.redis_client.hmset(performance_key, self.performance_metrics)
        
        logger.info(
            f"거래 성과 업데이트 - 결과: {trading_result}, "
            f"승률: {self.performance_metrics['current_win_rate']:.3f}, "
            f"연속 손실: {self.consecutive_loss_count}"
        )

    def get_current_performance_metrics(self) -> Dict[str, Any]:
        """현재 성과 지표 조회
        
        Returns:
            성과 통계가 포함된 API 응답
        """
        return create_api_response(
            success=True,
            data=self.performance_metrics,
            message="성과 지표 조회 완료"
        )

    def generate_comprehensive_trading_signal(self, symbol: str) -> TradingSignal:
        """다중 타임프레임 분석을 통한 종합적인 거래 신호 생성
        
        Args:
            symbol: 분석할 거래 심볼
            
        Returns:
            생성된 거래 신호 객체
        """
        # 신호 생성 조건 검증
        can_generate, rejection_reason = self._validate_signal_generation_conditions(symbol)
        if not can_generate:
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(), 
                signal=TRADING["SIGNALS"]["HOLD"], 
                confidence_score=0.0, 
                message=rejection_reason
            )

        try:
            # 다중 타임프레임 데이터 로드
            short_timeframe_data = self._load_market_data_with_cache(symbol, "1m")
            long_timeframe_data = self._load_market_data_with_cache(symbol, "15m")
            
            # 데이터 충분성 검증
            if len(short_timeframe_data) < 50 or len(long_timeframe_data) < 2:
                return TradingSignal(
                    symbol=symbol, 
                    timestamp=datetime.now(), 
                    signal=TRADING["SIGNALS"]["HOLD"], 
                    confidence_score=0.0, 
                    message="분석에 필요한 데이터 부족"
                )

            latest_short_data = short_timeframe_data.iloc[0]

            # 타임프레임별 추세 분석
            long_trend_analysis = self._analyze_long_timeframe_trend(long_timeframe_data)
            short_trend_analysis = self._analyze_short_timeframe_trend(latest_short_data)

            # 모멘텀 분석 (단기 추세 컨텍스트 활용)
            momentum_score, momentum_details = self._calculate_momentum_score(short_timeframe_data, short_trend_analysis)
            
            # 거래량 및 변동성 분석
            volume_weight, volume_details = self._analyze_volume_and_volatility(latest_short_data)
            
            # 종합 신호 점수 계산
            comprehensive_score = momentum_score * volume_weight * short_trend_analysis["strength"]
            
            # 장기 추세 필터를 통한 신호 결정
            final_signal = TRADING["SIGNALS"]["HOLD"]
            long_term_trend = long_trend_analysis["trend"]
            
            if comprehensive_score > 0.4 and "UP" in long_term_trend:
                final_signal = TRADING["SIGNALS"]["BUY"]
            elif comprehensive_score < -0.4 and "DOWN" in long_term_trend:
                final_signal = TRADING["SIGNALS"]["SELL"]
            
            # 포지션 크기 및 손절선 수준 계산
            optimal_position_size = self._calculate_optimal_position_size(latest_short_data)
            stop_loss_level = self._calculate_stop_loss_level(latest_short_data, final_signal)
            
            # 신호 생성 시간 기록
            self.last_signal_timestamps[symbol] = datetime.now()
            
            # 상세 메타데이터 구성
            signal_metadata = {
                "long_term_trend": long_trend_analysis,
                "short_term_trend": short_trend_analysis,
                "momentum": momentum_details,
                "volume": volume_details,
                "technical_indicators": {
                    "close_price": float(latest_short_data.get("close", 0)),
                    "atr": float(latest_short_data.get("atr", 0)),
                    "rsi": float(latest_short_data.get("rsi_14", 50)),
                    "macd_hist": float(latest_short_data.get("macd_hist", 0))
                }
            }
            
            # 거래 신호 객체 생성
            trading_signal = TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(), 
                signal=final_signal,
                confidence_score=float(abs(comprehensive_score)), 
                position_size=float(optimal_position_size),
                stop_loss_price=float(stop_loss_level), 
                metadata=signal_metadata
            )
            
            # 신호 이력 저장
            self.signal_history_buffer.append({
                "symbol": symbol, 
                "timestamp": datetime.now().isoformat(), 
                "signal": final_signal,
                "confidence": float(abs(comprehensive_score)), 
                "comprehensive_score": float(comprehensive_score)
            })
            
            return trading_signal

        except DataNotFoundException as e:
            logger.warning(f"{symbol} 신호 생성 실패: {e}")
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(), 
                signal=TRADING["SIGNALS"]["HOLD"], 
                confidence_score=0.0, 
                message=str(e)
            )
        except Exception as e:
            logger.error(f"{symbol} 신호 생성 중 예상치 못한 오류 발생: {e}", exc_info=True)
            return TradingSignal(
                symbol=symbol, 
                timestamp=datetime.now(), 
                signal=TRADING["SIGNALS"]["HOLD"], 
                confidence_score=0.0, 
                message="내부 서버 오류로 인한 신호 생성 실패"
            )


# 하위 호환성을 위한 클래스 별칭
SignalService = TradingSignalAnalyzer
