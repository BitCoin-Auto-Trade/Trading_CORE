
"""
매매 신호 관련 비즈니스 로직을 처리하는 서비스 모듈입니다.
"""
from app.schemas.signal import TradingSignal
from app.services.historical_data_service import HistoricalDataService
from app.services.realtime_data_service import RealtimeDataService

class SignalService:
    """
    매매 신호 생성을 위한 서비스 클래스.
    - `historical_data_service`: HistoricalDataService 인스턴스
    - `realtime_data_service`: RealtimeDataService 인스턴스
    """
    def __init__(self, historical_data_service: HistoricalDataService, realtime_data_service: RealtimeDataService):
        self.historical_data_service = historical_data_service
        self.realtime_data_service = realtime_data_service

    def get_trading_signal_by_rsi(self, symbol: str) -> TradingSignal:
        """
        RSI 값을 기반으로 매매 신호를 생성합니다.
        - 30 이하 과매도 -> 매수
        - 70 이상 과매수 -> 매도
        """
        latest_kline = self.historical_data_service.get_klines_data(symbol, limit=1)

        if not latest_kline or latest_kline[0].rsi_14 is None:
            return TradingSignal(symbol=symbol, signal="HOLD", message="RSI 데이터를 사용할 수 없습니다.")

        rsi_value = latest_kline[0].rsi_14
        timestamp = latest_kline[0].timestamp

        if rsi_value <= 30:
            signal = "BUY"
            message = f"RSI({rsi_value:.2f}) <= 30, 과매도 구간. 매수 고려."
        elif rsi_value >= 70:
            signal = "SELL"
            message = f"RSI({rsi_value:.2f}) >= 70, 과매수 구간. 매도 고려."
        else:
            signal = "HOLD"
            message = f"RSI({rsi_value:.2f}), 중립 구간. 관망."

        return TradingSignal(symbol=symbol, timestamp=timestamp, rsi_value=rsi_value, signal=signal, message=message)

    def get_trading_signal_by_macd(self, symbol: str) -> TradingSignal:
        """
        MACD 값을 기반으로 매매 신호를 생성합니다.
        - 골든 크로스 (MACD > Signal) -> 매수
        - 데드 크로스 (MACD < Signal) -> 매도
        """
        klines = self.historical_data_service.get_klines_data(symbol, limit=2)

        if len(klines) < 2 or klines[0].macd is None or klines[0].macd_signal is None or \
           klines[1].macd is None or klines[1].macd_signal is None:
            return TradingSignal(symbol=symbol, signal="HOLD", message="MACD 데이터를 사용할 수 없습니다.")

        current_kline = klines[0]
        previous_kline = klines[1]

        signal = "HOLD"
        message = f"MACD({current_kline.macd:.2f}), Signal({current_kline.macd_signal:.2f}). 관망."

        # 골든 크로스
        if current_kline.macd > current_kline.macd_signal and previous_kline.macd <= previous_kline.macd_signal:
            signal = "BUY"
            message = f"MACD 골든 크로스 발생. 매수 고려."
        # 데드 크로스
        elif current_kline.macd < current_kline.macd_signal and previous_kline.macd >= previous_kline.macd_signal:
            signal = "SELL"
            message = f"MACD 데드 크로스 발생. 매도 고려."

        return TradingSignal(
            symbol=symbol,
            timestamp=current_kline.timestamp,
            macd_value=current_kline.macd,
            macd_signal_value=current_kline.macd_signal,
            macd_hist_value=current_kline.macd_hist,
            signal=signal,
            message=message
        )

    def get_combined_trading_signal(self, symbol: str) -> TradingSignal:
        """
        RSI와 MACD 신호를 결합하여 종합 매매 신호를 생성합니다.
        - 두 신호가 모두 매수/매도일 경우 -> 강력 매수/매도
        - 한 신호만 매수/매도일 경우 -> 매수/매도
        - 그 외 -> 관망
        """
        rsi_signal = self.get_trading_signal_by_rsi(symbol)
        macd_signal = self.get_trading_signal_by_macd(symbol)

        # 두 신호의 방향을 정수로 표현 (BUY: 1, SELL: -1, HOLD: 0)
        rsi_direction = 1 if rsi_signal.signal == "BUY" else -1 if rsi_signal.signal == "SELL" else 0
        macd_direction = 1 if macd_signal.signal == "BUY" else -1 if macd_signal.signal == "SELL" else 0
        
        combined_direction = rsi_direction + macd_direction

        if combined_direction > 1:
            signal = "STRONG_BUY"
            message = f"RSI & MACD 동시 매수 신호. {rsi_signal.message} {macd_signal.message}"
        elif combined_direction < -1:
            signal = "STRONG_SELL"
            message = f"RSI & MACD 동시 매도 신호. {rsi_signal.message} {macd_signal.message}"
        elif combined_direction == 1:
            signal = "BUY"
            message = "RSI 또는 MACD 매수 신호 발생."
        elif combined_direction == -1:
            signal = "SELL"
            message = "RSI 또는 MACD 매도 신호 발생."
        else:
            signal = "HOLD"
            message = "매매 신호 없음. 관망."

        return TradingSignal(
            symbol=symbol,
            timestamp=rsi_signal.timestamp,
            rsi_value=rsi_signal.rsi_value,
            macd_value=macd_signal.macd_value,
            macd_signal_value=macd_signal.macd_signal_value,
            macd_hist_value=macd_signal.macd_hist_value,
            signal=signal,
            message=message
        )

