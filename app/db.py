# app/db.py
from __future__ import annotations

from typing import AsyncGenerator
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings


# === 1. Общая база для всех моделей ===
class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


# === 2. Настройка движка ===
# Пример DSN: postgresql+asyncpg://app:app@db:5432/app
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)


# === 3. Сессия ===
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# === 4. Депенденси для FastAPI и сервисов ===
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Асинхронная сессия SQLAlchemy."""
    async with SessionLocal() as session:
        yield session
