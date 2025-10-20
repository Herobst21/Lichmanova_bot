# app/scheduler/jobs.py
from __future__ import annotations

import os
from typing import Set, Tuple

from aiogram.client.bot import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.services.access_service import AccessService

# Эти переменные нужны не для джобы самой по себе,
# но часто удобно иметь их под рукой (логи/диагностика).
CONTENT_CHANNEL_ID = int(os.getenv("CONTENT_CHANNEL_ID", "0"))
CONTENT_CHAT_ID = int(os.getenv("CONTENT_CHAT_ID", "0"))


async def revoke_expired_job(bot: Bot) -> None:
    """
    Периодическая задача: находит просроченные доступы и выгоняет людей из чатов.
    Идём по записям access_grants с access_expires_at < now.
    """
    async with SessionLocal() as session:  # type: AsyncSession
        svc = AccessService(session, bot)

        expired = await svc.get_expired_accesses()
        if not expired:
            return

        # Не пинаем одного и того же юзера по одному чату много раз.
        seen: Set[Tuple[int, int]] = set()
        for g in expired:
            key = (g.tg_user_id, g.chat_id)
            if key in seen:
                continue
            seen.add(key)

            try:
                await svc.revoke_access(chat_id=g.chat_id, user_id=g.tg_user_id)
            except Exception:
                # Тут можно логировать, если у тебя есть общий logger.
                # Но падать не нужно: едем дальше.
                pass


def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """
    Регистрирует все периодические задачи.
    Вызывается один раз при старте приложения.
    """
    scheduler.add_job(
        revoke_expired_job,
        trigger="interval",
        minutes=10,               # каждые 10 минут
        kwargs={"bot": bot},
        id="revoke_expired_job",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,    # если проспали, даём минуту на отработку
    )
