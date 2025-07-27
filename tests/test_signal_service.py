"""
신호 서비스 테스트
"""
from unittest.mock import Mock, patch
import pytest
from datetime import datetime

from app.services.signal_service import SignalService
from app.schemas.core import TradingSignal

class TestSignalService:
    """SignalService 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.mock_db_repo = Mock()
        self.mock_binance_adapter = Mock()
        self.mock_redis = Mock()
        
        self.signal_service = SignalService(
            db_repository=self.mock_db_repo,
            binance_adapter=self.mock_binance_adapter,
            redis_client=self.mock_redis
        )
    
    def test_get_combined_trading_signal_hold(self):
        """HOLD 신호 생성 테스트"""
        # Mock 데이터 설정
        self.mock_db_repo.get_klines_by_symbol_as_df.return_value = Mock()
        
        with patch.object(self.signal_service, '_prepare_data') as mock_prepare:
            mock_prepare.return_value = Mock()
            mock_prepare.return_value.__len__ = Mock(return_value=100)
            mock_prepare.return_value.iloc = [Mock()]
            
            signal = self.signal_service.get_combined_trading_signal("BTCUSDT")
            
            assert isinstance(signal, TradingSignal)
            assert signal.symbol == "BTCUSDT"
            assert signal.signal in ["BUY", "SELL", "HOLD"]
    
    def test_performance_tracking(self):
        """성과 추적 테스트"""
        initial_stats = self.signal_service.performance_stats.copy()
        
        # WIN 결과 업데이트
        self.signal_service.update_performance("WIN")
        assert self.signal_service.performance_stats["successful_signals"] == initial_stats["successful_signals"] + 1
        
        # LOSS 결과 업데이트
        self.signal_service.update_performance("LOSS")
        assert self.signal_service.performance_stats["failed_signals"] == initial_stats["failed_signals"] + 1
    
    def test_signal_cooldown(self):
        """신호 쿨다운 테스트"""
        symbol = "BTCUSDT"
        
        # 첫 번째 신호는 정상 생성되어야 함
        can_signal, reason = self.signal_service._should_generate_signal(symbol)
        assert can_signal == True
        
        # 쿨다운 시간 내에서는 신호 생성이 제한되어야 함
        self.signal_service.last_signal_time[symbol] = datetime.now()
        can_signal, reason = self.signal_service._should_generate_signal(symbol)
        assert can_signal == False
        assert "쿨다운" in reason
