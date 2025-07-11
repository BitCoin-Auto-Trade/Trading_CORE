"""
주문 관련 비즈니스 로직을 처리하는 서비스 모듈입니다.
"""
from app.services.realtime_data_service import RealtimeDataService

class OrderService:
    """
    주문 관련 로직을 위한 서비스 클래스.
    - `realtime_data_service`: RealtimeDataService 인스턴스
    """
    def __init__(self, realtime_data_service: RealtimeDataService):
        self.realtime_data_service = realtime_data_service
        # 주문 관련 로직 추가 예정
