# app/middlewares/deps.py
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession


class DepsMiddleware(BaseMiddleware):
    def __init__(self, *, session: AsyncSession, services: Dict[str, Any]) -> None:
        self.session = session
        self.services = services

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Инжектим сессию
        data["session"] = self.session

        # Инжектим сервисы по тем ключам, которые ждут хендлеры
        # Пример: def cmd_start(message: Message, payments: PaymentService, subs: SubscriptionService, session: AsyncSession)
        for k, v in self.services.items():
            data[k] = v

        return await handler(event, data)
