
"""
매매 신호 관련 비즈니스 로직을 처리하는 서비스 모듈입니다.

- 과거 데이터(RSI, MACD)와 실시간 데이터(오더북, 체결량)를 종합하여 정교한 매매 신호를 생성합니다.
"""
from app.schemas.signal_schema import TradingSignal
from app.services.historical_data_service import HistoricalDataService
from app.services.realtime_data_service import RealtimeDataService

class SignalService:
    """
    매매 신호 생성을 위한 서비스 클래스.

    - `historical_data_service`: 과거 데이터(DB) 조회 서비스
    - `realtime_data_service`: 실시간 데이터(Redis) 조회 서비스
    """
    def __init__(self, historical_data_service: HistoricalDataService, realtime_data_service: RealtimeDataService):
        self.historical_data_service = historical_data_service
        self.realtime_data_service = realtime_data_service

    def _analyze_order_book_imbalance(self, symbol: str) -> tuple[str, float]:
        """
        실시간 오더북을 분석하여 매수/매도 압력을 파악합니다.
        - 매수벽이 매도벽보다 1.5배 이상 두꺼우면 매수 우위.
        - 매도벽이 매수벽보다 1.5배 이상 두꺼우면 매도 우위.
        
        Returns:
            - signal (str): "BUY", "SELL", "HOLD"
            - score (float): 신호 강도 점수
        """
        order_book = self.realtime_data_service.get_order_book(symbol)
        if not order_book or not order_book.get('bids') or not order_book.get('asks'):
            return "HOLD", 0

        total_bid_volume = sum(float(bid[1]) for bid in order_book['bids'])
        total_ask_volume = sum(float(ask[1]) for ask in order_book['asks'])

        if total_bid_volume > total_ask_volume * 1.5:
            return "BUY", 1.0
        elif total_ask_volume > total_bid_volume * 1.5:
            return "SELL", -1.0
        return "HOLD", 0

    def _analyze_trade_flow(self, symbol: str) -> tuple[str, float]:
        """
        최근 체결 내역을 분석하여 시장의 공격적인 방향성을 파악합니다.
        - Taker Buy: 시장가 매수 (공격적 매수)
        - Taker Sell: 시장가 매도 (공격적 매도)

        Returns:
            - signal (str): "BUY", "SELL", "HOLD"
            - score (float): 신호 강도 점수
        """
        trades = self.realtime_data_service.get_trades(symbol, limit=50)
        if not trades:
            return "HOLD", 0

        taker_buys = sum(1 for trade in trades if not trade.get('m')) # m=False is Taker Buy
        taker_sells = sum(1 for trade in trades if trade.get('m')) # m=True is Taker Sell

        if taker_buys > taker_sells * 1.5:
            return "BUY", 1.0
        elif taker_sells > taker_buys * 1.5:
            return "SELL", -1.0
        return "HOLD", 0

    def get_trading_signal_by_rsi(self, symbol: str) -> tuple[str, float, TradingSignal]:
        """
        RSI 지표를 기반으로 매매 신호를 생성합니다.
        """
        latest_kline = self.historical_data_service.get_klines_data(symbol, limit=1)
        if not latest_kline or latest_kline[0].rsi_14 is None:
            return "HOLD", 0, TradingSignal(symbol=symbol, signal="HOLD", message="RSI 데이터 부족")

        rsi_value = latest_kline[0].rsi_14
        signal = "HOLD"
        score = 0
        if rsi_value <= 30: # 과매도
            signal, score = "BUY", 1.0
        elif rsi_value >= 70: # 과매수
            signal, score = "SELL", -1.0
        
        return signal, score, TradingSignal(symbol=symbol, rsi_value=rsi_value, signal=signal)

    def get_trading_signal_by_macd(self, symbol: str) -> tuple[str, float, TradingSignal]:
        """
        MACD 지표를 기반으로 매매 신호를 생성합니다.
        """
        klines = self.historical_data_service.get_klines_data(symbol, limit=2)
        if len(klines) < 2 or klines[0].macd is None or klines[0].macd_signal is None:
            return "HOLD", 0, TradingSignal(symbol=symbol, signal="HOLD", message="MACD 데이터 부족")

        current_kline, previous_kline = klines[0], klines[1]
        signal = "HOLD"
        score = 0
        # 골든 크로스
        if current_kline.macd > current_kline.macd_signal and previous_kline.macd <= previous_kline.macd_signal:
            signal, score = "BUY", 1.0
        # 데드 크로스
        elif current_kline.macd < current_kline.macd_signal and previous_kline.macd >= previous_kline.macd_signal:
            signal, score = "SELL", -1.0

        return signal, score, TradingSignal(
            symbol=symbol, 
            macd_value=current_kline.macd, 
            macd_signal_value=current_kline.macd_signal,
            signal=signal
        )

    def get_combined_trading_signal(self, symbol: str) -> TradingSignal:
        """
        모든 지표(RSI, MACD, 오더북, 거래흐름)를 종합하여 최종 매매 신호를 생성합니다.
        - 각 지표의 점수를 합산하여 최종 신호를 결정합니다.
        - 점수 체계: BUY(1), SELL(-1), STRONG_BUY(2), STRONG_SELL(-2)
        """
        # 1. 각 지표별 신호 및 점수 계산
        rsi_signal, rsi_score, rsi_obj = self.get_trading_signal_by_rsi(symbol)
        macd_signal, macd_score, macd_obj = self.get_trading_signal_by_macd(symbol)
        ob_signal, ob_score = self._analyze_order_book_imbalance(symbol)
        tf_signal, tf_score = self._analyze_trade_flow(symbol)

        # 2. 최종 점수 합산
        total_score = rsi_score + macd_score + ob_score + tf_score

        # 3. 최종 신호 및 메시지 결정
        final_signal = "HOLD"
        if total_score >= 2.0:
            final_signal = "STRONG_BUY"
        elif total_score > 0:
            final_signal = "BUY"
        elif total_score <= -2.0:
            final_signal = "STRONG_SELL"
        elif total_score < 0:
            final_signal = "SELL"

        message = (
            f"Final Signal: {final_signal} (Score: {total_score:.1f})\n"
            f"- RSI: {rsi_signal} (Score: {rsi_score:.1f}, Value: {rsi_obj.rsi_value:.2f})\n"
            f"- MACD: {macd_signal} (Score: {macd_score:.1f})\n"
            f"- Order Book: {ob_signal} (Score: {ob_score:.1f})\n"
            f"- Trade Flow: {tf_signal} (Score: {tf_score:.1f})"
        )

        return TradingSignal(
            symbol=symbol,
            timestamp=self.historical_data_service.get_klines_data(symbol, limit=1)[0].timestamp,
            rsi_value=rsi_obj.rsi_value,
            macd_value=macd_obj.macd_value,
            macd_signal_value=macd_obj.macd_signal_value,
            signal=final_signal,
            message=message
        )

