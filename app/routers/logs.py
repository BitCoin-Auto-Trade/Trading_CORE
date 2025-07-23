"""
실시간 로그 모니터링을 위한 WebSocket 및 REST API 라우터입니다.
"""

from fastapi import APIRouter, WebSocket
import asyncio
import logging
import json
from collections import deque

from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# 메모리 기반 로그 버퍼
log_buffer = deque(maxlen=1000)  # 최근 1000개 로그만 유지

class WebSocketLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.connections = set()
    
    def emit(self, record):
        log_entry = {
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": self.format(record),
            "module": getattr(record, 'module', ''),
        }
        log_buffer.append(log_entry)
        
        # 연결된 모든 WebSocket에 전송
        if self.connections:
            asyncio.create_task(self.broadcast_log(log_entry))
    
    async def broadcast_log(self, log_entry):
        """연결된 모든 WebSocket 클라이언트에게 로그 메시지를 전송합니다."""
        if not self.connections:
            return
            
        disconnected = set()
        for websocket in self.connections:
            try:
                await websocket.send_text(json.dumps(log_entry))
            except Exception as e:
                disconnected.add(websocket)
        
        # 끊어진 연결 제거
        if disconnected:
            self.connections -= disconnected
            logger.debug(f"WebSocket 연결 {len(disconnected)}개 제거됨")

# 전역 WebSocket 핸들러
ws_handler = WebSocketLogHandler()

# 기존 로거들에 WebSocket 핸들러 추가
def setup_websocket_logging():
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s %(name)s: %(message)s')
    ws_handler.setFormatter(formatter)
    
    # 주요 로거들에 핸들러 추가
    loggers = [
        'app.core.scheduler',
        'app.services.signal_service', 
        'app.services.order_service',
        'app.adapters.binance_adapter',
        'app.main',
        'root'
    ]
    
    for logger_name in loggers:
        logging.getLogger(logger_name).addHandler(ws_handler)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket을 통한 실시간 로그 스트리밍 엔드포인트"""
    await websocket.accept()
    ws_handler.connections.add(websocket)
    
    try:
        # 연결 시 최근 로그 전송
        for log_entry in list(log_buffer):
            await websocket.send_text(json.dumps(log_entry))
        
        # 연결 유지 (heartbeat)
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # 30초마다 ping 전송
                await websocket.ping()
    except Exception as e:
        logger.debug(f"WebSocket 연결 종료: {e}")
    finally:
        ws_handler.connections.discard(websocket)

@router.get("/recent")
async def get_recent_logs(limit: int = 100):
    """최근 로그 조회 API"""
    recent_logs = list(log_buffer)[-limit:]
    return {"logs": recent_logs}