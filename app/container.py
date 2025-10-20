# app/container.py
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal, engine  # реэкспорт для main.py
from app.models.base import Base

from app.repositories.subscription_repo import SubscriptionRepo
from app.repositories.payment_repo import PaymentRepo
from app.repositories.user_repo import UserRepo

from app.services.subscription_service import SubscriptionService
from app.services.payment_service import PaymentService


async def init_db() -> None:
    """
    Dev-инициализация БД: создаём таблицы, если их нет.
    В проде используй alembic upgrade head.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def build_dp(bot: Bot) -> Dispatcher:
    """
    Собираем Dispatcher для aiogram 3.x.
    """
    storage = RedisStorage.from_url(settings.REDIS_DSN)
    dp = Dispatcher(storage=storage)
    return dp


async def build_services(bot: Bot, session: AsyncSession):
    """
    Единая сборка сервисов и репозиториев. Возвращаем словарь.
    """
    # repos
    subs_repo = SubscriptionRepo(session)
    pay_repo = PaymentRepo(session)
    users_repo = UserRepo(session)

    # services
    subs_svc = SubscriptionService(subs_repo)
    pay_svc = PaymentService(session)  # внутри сам подтянет repo-классы

    return {
        "subscriptions": subs_svc,
        "payments": pay_svc,
        "repos": {
            "subscriptions": subs_repo,
            "payments": pay_repo,
            "users": users_repo,
        },
    }
