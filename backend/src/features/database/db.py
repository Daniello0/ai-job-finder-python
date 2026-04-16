from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from features.database.settings import build_database_url


engine = create_async_engine(build_database_url(), pool_pre_ping=True)
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session (FastAPI-ready dependency)."""
    async with async_session_factory() as session:
        yield session

