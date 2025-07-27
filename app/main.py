"""
Trading CORE API - 메인 애플리케이션
"""
from app.core.application import create_application

# FastAPI 애플리케이션 인스턴스
app = create_application()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
