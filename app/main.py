# app/main.py
from __future__ import annotations

import os
import asyncio
import logging
import signal
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import AsyncSession

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.jobs import setup_scheduler

from app.config import settings
from app.core.logging import setup_logging, attach_ctx_filter
from app.container import build_dp, build_services, init_db
from app.db import SessionLocal, engine
from app.middlewares.deps import DepsMiddleware
from app.middlewares.logging import LoggingMiddleware
from app.handlers.members import router as members_router

# ---- Логи первыми ----
setup_logging()
attach_ctx_filter()
logger = logging.getLogger("app.main")

# ---- Роутеры: один /start, без дублей ----
from app.handlers import id_cmd
from app.handlers.start import router as start_router
from app.handlers.payments_rk import router as payments_rk_router
from app.handlers.pay import router as pay_router
from app.handlers.errors import router as errors_router
from app.handlers.age_verify import router as age_verify_router  # NEW: U18 верификация


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать"),
            BotCommand(command="admin", description="Админ-панель"),
        ]
    )


async def main() -> None:
    logger.info(
        "boot: starting with LOG_LEVEL=%s SQL_ECHO=%s provider=%s",
        settings.log_level,
        settings.SQL_ECHO,
        settings.PAYMENT_PROVIDER,
    )

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # На всякий: сносим вебхук, чтобы polling не конфликтовал
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        logger.warning("delete_webhook failed; continue with polling")

    dp: Dispatcher = await build_dp(bot)

    # DB init: в проде миграции через Alembic, create_all только если явно включили
    if os.getenv("INIT_DB_ON_START", "0") == "1":
        try:
            await init_db()
            logger.info("DB init done (create_all enabled by ENV)")
        except Exception:
            logger.exception("DB init failed (dev-only path)")
    else:
        logger.info("DB init skipped (use alembic upgrade head)")

    session: AsyncSession = SessionLocal()
    services: dict[str, Any] = await build_services(bot, session)

    inject: dict[str, Any] = {
        "session": session,
        "payments": services.get("payments"),
        "subs": services.get("subscriptions"),
    }

    # Middlewares
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.middleware(DepsMiddleware(session=session, services=inject))

    # Routers — порядок важен
    dp.include_routers(
        id_cmd.router,
        start_router,
        age_verify_router,
        payments_rk_router,
        pay_router,
        members_router,   # новый
        errors_router,
    )

    await setup_bot_commands(bot)
    logger.info("Commands set, start polling")

    # ---------- Scheduler ----------
    scheduler = AsyncIOScheduler(timezone="UTC")
    setup_scheduler(scheduler, bot)
    scheduler.start()

    # Корректное завершение по сигналам
    stop_evt = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _stop(*_: object) -> None:
        stop_evt.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    async def _poll():
        try:
            await dp.start_polling(bot, handle_signals=False)
        except asyncio.CancelledError:
            pass

    poll_task = asyncio.create_task(_poll())
    await stop_evt.wait()

    # ---------- Shutdown ----------
    try:
        await dp.stop_polling()
    except Exception:
        pass

    # Останавливаем scheduler
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("scheduler shutdown failed")

    if not poll_task.done():
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass

    # graceful storage
    try:
        await dp.storage.close()
        try:
            await dp.storage.wait_closed()  # type: ignore[attr-defined]
        except AttributeError:
            pass
    except Exception:
        logger.exception("storage close failed")

    # close bot session
    try:
        await bot.session.close()
    except Exception:
        logger.exception("bot session close failed")

    # close DB session
    try:
        await session.close()
    except Exception:
        logger.exception("db session close failed")

    # dispose engine
    try:
        await engine.dispose()
    except Exception:
        logger.exception("engine dispose failed")


if __name__ == "__main__":
    asyncio.run(main())
