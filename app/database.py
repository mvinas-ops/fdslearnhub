from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# IMPORTANT FOR WINDOWS + PYTEST + ASYNCPG:
# pytest-asyncio commonly creates/closes an event loop per test. Reusing asyncpg
# pooled connections across those loops causes: RuntimeError: Event loop is closed
# and AttributeError: 'NoneType' object has no attribute 'send'. NullPool avoids
# cross-loop connection reuse while keeping the runtime API production-compatible.
engine_kwargs = {
    "echo": False,
    "connect_args": connect_args,
}
if DATABASE_URL.startswith("postgresql+asyncpg"):
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(DATABASE_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
