"""
데이터베이스 연결 및 세션 관리 모듈.

SQLAlchemy 비동기 엔진과 세션 팩토리를 설정하고,
FastAPI 의존성 주입(Depends)에 사용할 get_db 제너레이터를 제공한다.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 비동기 DB 엔진 (asyncpg 드라이버 사용)
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

# 비동기 세션 팩토리 - expire_on_commit=False로 커밋 후에도 객체 속성 접근 가능
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """모든 ORM 모델의 기반 클래스. Alembic 마이그레이션에서 metadata를 참조한다."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI Depends에서 사용하는 DB 세션 제너레이터.
    요청 처리가 끝나면 세션이 자동으로 닫힌다."""
    async with async_session_factory() as session:
        yield session
