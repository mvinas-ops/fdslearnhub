# app/database.py

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# Allow pasted Neon/Render URLs copied as postgresql://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Remove URL params that commonly break asyncpg
DATABASE_URL = DATABASE_URL.replace("?sslmode=require", "")
DATABASE_URL = DATABASE_URL.replace("&sslmode=require", "")
DATABASE_URL = DATABASE_URL.replace("?ssl=require", "")
DATABASE_URL = DATABASE_URL.replace("&ssl=require", "")
DATABASE_URL = DATABASE_URL.replace("?channel_binding=require", "")
DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "")

connect_args = {}

# Neon requires SSL
if "neon.tech" in DATABASE_URL:
    connect_args = {"ssl": True}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    poolclass=NullPool,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
