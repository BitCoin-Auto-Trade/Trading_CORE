
"""
매매 신호 관련 비즈니스 로직을 처리하는 서비스 모듈입니다.

- 과거 데이터(RSI, MACD)와 실시간 데이터(오더북, 체결량)를 종합하여 정교한 매매 신호를 생성합니다.
"""
import pandas as pd
import pandas_ta as ta
from app.schemas.signal_schema import TradingSignal
from app.services.historical_data_service import HistoricalDataService
from app.services.realtime_data_service import RealtimeDataService

class SignalService:
    """
    매매 신호 생성을 위한 서비스 클래스.
    """
    def __init__(self, historical_data_service: HistoricalDataService, realtime_data_service: RealtimeDataService):
        self.historical_data_service = historical_data_service
        self.realtime_data_service = realtime_data_service
        # 손절/익절 설정
        self.atr_multiplier = 2.0  # ATR 기반 손절을 위한 승수
        self.tp_percentage = 0.015 # 1.5% 익절

    def _prepare_data_with_indicators(self, symbol: str) -> pd.DataFrame:
        """
        DB에서 K-line 데이터를 가져와 DataFrame으로 만들고, 
        부족한 지표(ATR)만 추가로 계산합니다.
        """
        klines = self.historical_data_service.get_klines_data(symbol, limit=200)
        if not klines:
            return pd.DataFrame()

        df = pd.DataFrame([k.__dict__ for k in klines])
        df = df.set_index('timestamp').sort_index()

        # pandas-ta를 사용하여 ATR만 추가로 계산합니다.
        # RSI와 MACD는 DB에 저장된 값을 사용합니다.
        df.ta.atr(length=14, append=True)
        
        # DB에서 가져온 값의 컬럼명을 pandas-ta 표준 컬럼명과 유사하게 맞춰줍니다.
        df.rename(columns={
            'rsi_14': 'RSI_14',
            'macd': 'MACD_12_26_9',
            'macd_signal': 'MACDs_12_26_9',
            'macd_hist': 'MACDh_12_26_9',
            'atr': 'ATRr_14' # ATR 컬럼명도 통일
        }, inplace=True)

        return df.iloc[::-1] # 최신 데이터가 위로 오도록 다시 정렬

    def _analyze_technical_indicators(self, df: pd.DataFrame) -> tuple[str, float, dict]:
        """
        계산된 기술적 지표(RSI, MACD)를 바탕으로 신호와 점수를 반환합니다.
        """
        if len(df) < 2 or 'RSI_14' not in df.columns or df['RSI_14'].isnull().all():
            return "HOLD", 0, {}

        latest = df.iloc[0]
        previous = df.iloc[1]

        # RSI 신호 (DB에서 가져온 값 사용)
        rsi_signal, rsi_score = "HOLD", 0
        if latest['RSI_14'] <= 30:
            rsi_signal, rsi_score = "BUY", 1.0
        elif latest['RSI_14'] >= 70:
            rsi_signal, rsi_score = "SELL", -1.0

        # MACD 신호 (DB에서 가져온 값 사용)
        macd_signal, macd_score = "HOLD", 0
        if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] and previous['MACD_12_26_9'] <= previous['MACDs_12_26_9']:
            macd_signal, macd_score = "BUY", 1.0
        elif latest['MACD_12_26_9'] < latest['MACDs_12_26_9'] and previous['MACD_12_26_9'] >= previous['MACDs_12_26_9']:
            macd_signal, macd_score = "SELL", -1.0
            
        tech_score = rsi_score + macd_score
        tech_info = {
            "rsi_signal": rsi_signal, "rsi_score": rsi_score, "rsi_value": latest['RSI_14'],
            "macd_signal": macd_signal, "macd_score": macd_score
        }
        return "BUY" if tech_score > 0 else "SELL" if tech_score < 0 else "HOLD", tech_score, tech_info

    def _analyze_market_data(self, symbol: str) -> tuple[str, float, dict]:
        """
        실시간 오더북과 체결량으로 시장 압력을 분석합니다.
        """
        # ... (이전과 동일) ...
        order_book = self.realtime_data_service.get_order_book(symbol)
        ob_signal, ob_score = "HOLD", 0
        if order_book and order_book.get('bids') and order_book.get('asks'):
            total_bid_volume = sum(float(bid[1]) for bid in order_book['bids'])
            total_ask_volume = sum(float(ask[1]) for ask in order_book['asks'])
            if total_bid_volume > total_ask_volume * 1.5:
                ob_signal, ob_score = "BUY", 1.0
            elif total_ask_volume > total_bid_volume * 1.5:
                ob_signal, ob_score = "SELL", -1.0

        trades = self.realtime_data_service.get_trades(symbol, limit=50)
        tf_signal, tf_score = "HOLD", 0
        if trades:
            taker_buys = sum(1 for trade in trades if not trade.get('m'))
            taker_sells = sum(1 for trade in trades if trade.get('m'))
            if taker_buys > taker_sells * 1.5:
                tf_signal, tf_score = "BUY", 1.0
            elif taker_sells > taker_buys * 1.5:
                tf_signal, tf_score = "SELL", -1.0
        
        market_score = ob_score + tf_score
        market_info = {
            "ob_signal": ob_signal, "ob_score": ob_score,
            "tf_signal": tf_signal, "tf_score": tf_score
        }
        return "BUY" if market_score > 0 else "SELL" if market_score < 0 else "HOLD", market_score, market_info

    def get_combined_trading_signal(self, symbol: str) -> TradingSignal:
        """
        모든 지표를 종합하여 최종 매매 신호와 손절/익절 가격을 생성합니다.
        """
        df = self._prepare_data_with_indicators(symbol)
        if df.empty or 'ATRr_14' not in df.columns or df['ATRr_14'].isnull().all():
            return TradingSignal(symbol=symbol, signal="HOLD", message="데이터 부족 또는 ATR 계산 불가")

        latest_kline = df.iloc[0]
        current_price = latest_kline['close']
        
        tech_signal, tech_score, tech_info = self._analyze_technical_indicators(df)
        market_signal, market_score, market_info = self._analyze_market_data(symbol)

        total_score = tech_score + market_score

        final_signal = "HOLD"
        if total_score >= 2.0: final_signal = "STRONG_BUY"
        elif total_score > 0: final_signal = "BUY"
        elif total_score <= -2.0: final_signal = "STRONG_SELL"
        elif total_score < 0: final_signal = "SELL"

        # --- 손절/익절 가격 계산 ---
        stop_loss_price, take_profit_price = None, None
        if final_signal in ["STRONG_BUY", "BUY"]:
            atr_value = latest_kline['ATRr_14']
            stop_loss_price = current_price - (atr_value * self.atr_multiplier)
            take_profit_price = current_price * (1 + self.tp_percentage)
        elif final_signal in ["STRONG_SELL", "SELL"]:
            atr_value = latest_kline['ATRr_14']
            stop_loss_price = current_price + (atr_value * self.atr_multiplier)
            take_profit_price = current_price * (1 - self.tp_percentage)

        message = (
            f"Final Signal: {final_signal} (Score: {total_score:.1f})\n"
            f"- Tech: {tech_signal} (Score: {tech_score:.1f}), Market: {market_signal} (Score: {market_score:.1f})\n"
            f"- RSI: {tech_info.get('rsi_value', 0):.2f}, MACD Cross: {tech_info.get('macd_signal', 'N/A')}\n"
            f"- SL: {stop_loss_price:.4f if stop_loss_price else 0}, TP: {take_profit_price:.4f if take_profit_price else 0} (ATR: {latest_kline['ATRr_14']:.4f})"
        )

        return TradingSignal(
            symbol=symbol,
            timestamp=latest_kline.name,
            rsi_value=tech_info.get('rsi_value'),
            macd_value=latest_kline.get('MACD_12_26_9'),
            macd_signal_value=latest_kline.get('MACDs_12_26_9'),
            signal=final_signal,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            message=message
        )

