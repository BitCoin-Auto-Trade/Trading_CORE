import redis
from sqlalchemy.orm import Session
from app.repository.signal import SignalRepository
from app.schemas.signal import TradingSignal

class SignalService:
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.signal_repo = SignalRepository(db=db, redis_client=redis_client)

    def get_klines(self, symbol: str, limit: int):
        """
        특정 심볼의 kline 데이터를 조회합니다.
        """
        return self.signal_repo.get_klines_by_symbol(symbol, limit)

    def get_funding_rates(self, symbol: str, limit: int):
        """
        특정 심볼의 펀딩비 데이터를 조회합니다.
        """
        return self.signal_repo.get_funding_rates_by_symbol(self.db, symbol, limit)

    def get_open_interest(self, symbol: str, limit: int):
        """
        특정 심볼의 미결제 약정 데이터를 조회합니다.
        """
        return self.signal_repo.get_open_interest_by_symbol(self.db, symbol, limit)

    def get_trading_signal_by_rsi(self, symbol: str) -> TradingSignal:
        """
        RSI 값을 기반으로 매매 신호를 생성합니다.
        """
        # 최신 kline 데이터 1개를 가져옵니다.
        latest_kline = self.signal_repo.get_klines_by_symbol(symbol, limit=1)

        if not latest_kline or latest_kline[0].get('rsi_14') is None:
            return TradingSignal(
                symbol=symbol,
                signal="HOLD",
                message="RSI 데이터가 없거나 유효하지 않습니다."
            )

        rsi_value = latest_kline[0]['rsi_14']
        timestamp = latest_kline[0]['timestamp']

        if rsi_value <= 30: # 과매도 구간
            signal = "BUY"
            message = f"RSI({rsi_value:.2f})가 30 이하로 과매도 구간입니다. 매수 고려."
        elif rsi_value >= 70: # 과매수 구간
            signal = "SELL"
            message = f"RSI({rsi_value:.2f})가 70 이상으로 과매수 구간입니다. 매도 고려."
        else:
            signal = "HOLD"
            message = f"RSI({rsi_value:.2f})가 중립 구간입니다. 관망."

        return TradingSignal(
            symbol=symbol,
            timestamp=timestamp,
            rsi_value=rsi_value,
            signal=signal,
            message=message
        )

    def get_trading_signal_by_macd(self, symbol: str) -> TradingSignal:
        """
        MACD 값을 기반으로 매매 신호를 생성합니다.
        """
        # MACD 신호는 최소 2개의 데이터 포인트가 필요합니다 (현재와 이전).
        klines = self.signal_repo.get_klines_by_symbol(symbol, limit=2)

        if len(klines) < 2 or klines[0].get('macd') is None or klines[0].get('macd_signal') is None or \
           klines[1].get('macd') is None or klines[1].get('macd_signal') is None:
            return TradingSignal(
                symbol=symbol,
                signal="HOLD",
                message="MACD 데이터가 충분하지 않거나 유효하지 않습니다."
            )

        current_kline = klines[0]
        previous_kline = klines[1]

        # 현재 MACD 값
        current_macd = current_kline['macd']
        current_macd_signal = current_kline['macd_signal']
        current_macd_hist = current_kline['macd_hist']

        # 이전 MACD 값
        previous_macd = previous_kline['macd']
        previous_macd_signal = previous_kline['macd_signal']

        signal = "HOLD"
        message = f"MACD({current_macd:.2f}), Signal({current_macd_signal:.2f}), Hist({current_macd_hist:.2f}). 관망."

        # 골든 크로스 (매수 신호): MACD 선이 시그널 선을 상향 돌파
        if current_macd > current_macd_signal and previous_macd <= previous_macd_signal:
            signal = "BUY"
            message = f"MACD({current_macd:.2f})가 Signal({current_macd_signal:.2f})을 상향 돌파했습니다. 매수 고려."
        # 데드 크로스 (매도 신호): MACD 선이 시그널 선을 하향 돌파
        elif current_macd < current_macd_signal and previous_macd >= previous_macd_signal:
            signal = "SELL"
            message = f"MACD({current_macd:.2f})가 Signal({current_macd_signal:.2f})을 하향 돌파했습니다. 매도 고려."

        return TradingSignal(
            symbol=symbol,
            timestamp=current_kline['timestamp'],
            rsi_value=current_kline.get('rsi_14'),
            macd_value=current_macd,
            macd_signal_value=current_macd_signal,
            macd_hist_value=current_macd_hist,
            signal=signal,
            message=message
        )

    def get_combined_trading_signal(self, symbol: str) -> TradingSignal:
        """
        RSI와 MACD 신호를 결합하여 종합 매매 신호를 생성합니다.
        여기에 오더북 깊이와 최근 체결 데이터를 활용합니다.
        """
        rsi_signal = self.get_trading_signal_by_rsi(symbol)
        macd_signal = self.get_trading_signal_by_macd(symbol)

        # Redis에서 오더북 깊이와 최근 체결 데이터 가져오기
        order_book_depth = self.signal_repo.get_order_book_depth(symbol)
        recent_trades = self.signal_repo.get_recent_trades(symbol)

        combined_signal = "HOLD"
        combined_message = ""

        # 오더북 깊이와 최근 체결 데이터를 활용한 추가 로직 (예시)
        # 실제 로직은 더 복잡하게 구현될 수 있습니다.
        if order_book_depth and recent_trades:
            # 간단한 예시: 매수 호가에 큰 물량이 있고, 최근 매수 체결이 많으면 매수 신호 강화
            # 이 부분은 실제 트레이딩 전략에 따라 복잡하게 구현될 수 있습니다.
            bids = order_book_depth.get('bids', [])
            asks = order_book_depth.get('asks', [])

            total_buy_volume = sum([float(b[1]) for b in bids])
            total_sell_volume = sum([float(a[1]) for a in asks])

            buy_trades_count = sum(1 for trade in recent_trades if trade.get('isBuyerMaker') == False) # isBuyerMaker가 False면 매수자가 시장가로 매수
            sell_trades_count = sum(1 for trade in recent_trades if trade.get('isBuyerMaker') == True) # isBuyerMaker가 True면 매도자가 시장가로 매도

            if total_buy_volume > total_sell_volume * 1.5 and buy_trades_count > sell_trades_count * 1.5:
                if rsi_signal.signal == "BUY" or macd_signal.signal == "BUY":
                    combined_signal = "STRONG_BUY"
                    combined_message = f"강력 매수: {rsi_signal.message} 그리고 {macd_signal.message}. 오더북 및 체결량 매수 우위."
            elif total_sell_volume > total_buy_volume * 1.5 and sell_trades_count > buy_trades_count * 1.5:
                if rsi_signal.signal == "SELL" or macd_signal.signal == "SELL":
                    combined_signal = "STRONG_SELL"
                    combined_message = f"강력 매도: {rsi_signal.message} 그리고 {macd_signal.message}. 오더북 및 체결량 매도 우위."

        # RSI와 MACD 신호가 모두 BUY일 때
        if rsi_signal.signal == "BUY" and macd_signal.signal == "BUY":
            if combined_signal != "STRONG_BUY": # 이미 강력 매수 신호가 아니면
                combined_signal = "STRONG_BUY"
                combined_message = f"강력 매수: {rsi_signal.message} 그리고 {macd_signal.message}"
        # RSI와 MACD 신호가 모두 SELL일 때
        elif rsi_signal.signal == "SELL" and macd_signal.signal == "SELL":
            if combined_signal != "STRONG_SELL": # 이미 강력 매도 신호가 아니면
                combined_signal = "STRONG_SELL"
                combined_message = f"강력 매도: {rsi_signal.message} 그리고 {macd_signal.message}"
        # RSI가 BUY이고 MACD가 HOLD일 때 (또는 그 반대)
        elif rsi_signal.signal == "BUY" or macd_signal.signal == "BUY":
            if combined_signal == "HOLD": # 오더북/체결량으로 신호가 없으면
                combined_signal = "BUY"
                combined_message = f"매수: {rsi_signal.message} 또는 {macd_signal.message}"
        # RSI가 SELL이고 MACD가 HOLD일 때 (또는 그 반대)
        elif rsi_signal.signal == "SELL" or macd_signal.signal == "SELL":
            if combined_signal == "HOLD": # 오더북/체결량으로 신호가 없으면
                combined_signal = "SELL"
                combined_message = f"매도: {rsi_signal.message} 또는 {macd_signal.message}"
        else:
            if combined_signal == "HOLD": # 오더북/체결량으로 신호가 없으면
                combined_signal = "HOLD"
                combined_message = f"관망: {rsi_signal.message} 그리고 {macd_signal.message}"

        # 종합 신호에 RSI와 MACD 값 포함
        return TradingSignal(
            symbol=symbol,
            timestamp=rsi_signal.timestamp if rsi_signal.timestamp else macd_signal.timestamp,
            rsi_value=rsi_signal.rsi_value,
            macd_value=macd_signal.macd_value,
            macd_signal_value=macd_signal.macd_signal_value,
            macd_hist_value=macd_signal.macd_hist_value,
            signal=combined_signal,
            message=combined_message
        )
