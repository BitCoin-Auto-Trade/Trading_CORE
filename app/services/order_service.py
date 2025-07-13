"""
주문 관련 비즈니스 로직을 처리합니다.
"""

from app.adapters.binance_adapter import BinanceAdapter


class OrderService:
    """
    주문 관련 로직을 위한 서비스 클래스입니다.
    """

    def __init__(self, binance_adapter: BinanceAdapter, testnet: bool = False):
        self.binance_adapter = binance_adapter
        # 주문 관련 로직 추가 예정
