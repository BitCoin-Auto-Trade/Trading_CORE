from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.db import engine, redis_client
from app.models import Base  # SQLAlchemy 모델의 Base를 가져옵니다.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    Base.metadata.create_all(bind=engine)
    try:
        redis_client.ping()
        print("Successfully connected to Redis")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
    yield
    # 종료 시 실행 (필요 시)

app = FastAPI(lifespan=lifespan)

# API 라우터 포함 (아직 라우터가 없으므로 주석 처리)
# from app.api import account, order, signal
# app.include_router(account.router, prefix="/accounts", tags=["accounts"])
# app.include_router(order.router, prefix="/orders", tags=["orders"])
# app.include_router(signal.router, prefix="/signals", tags=["signals"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading Core API"}
