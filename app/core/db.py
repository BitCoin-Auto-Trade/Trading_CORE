from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import redis
from app.core.config import settings

# PostgreSQL 연결
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis 연결
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
    decode_responses=True,
)


# DB 세션을 얻기 위한 Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis 클라이언트를 얻기 위한 Dependency
def get_redis():
    return redis_client
