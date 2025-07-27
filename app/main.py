"""
Trading CORE API - 메인 애플리케이션
"""
from app.core.application import create_application

# FastAPI 애플리케이션 인스턴스
app = create_application()

if __name__ == "__main__":
    import uvicorn
    
    # Uvicorn 로그 설정 (중복 방지)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="warning",  # Uvicorn 로그 레벨을 warning으로 설정
        access_log=False,     # Access 로그 비활성화 (LoggingMiddleware에서 처리)
    )
