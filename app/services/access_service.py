# app/services/access_service.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from aiogram.client.bot import Bot
class _TG_EXC_BASE(Exception): ...
try:
    # aiogram 3.* может кидать TelegramBadRequest
    from aiogram.exceptions import TelegramBadRequest  # type: ignore
except Exception:  # на всякий случай, чтобы не падать при импорте
    class TelegramBadRequest(_TG_EXC_BASE):  # type: ignore
        pass

from aiogram.types import ChatInviteLink, ChatMember

from sqlalchemy import insert, update, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.access_grant import AccessGrant


class AccessService:
    """
    Управляет доступом в канал/чат:
      - генерирует одноразовые инвайты
      - пишет выдачу в БД (access_grants)
      - проверяет членство
      - ищет свежие ссылки для реюза
      - отзывает доступ (кик) по истечению
    """

    def __init__(self, session: AsyncSession, bot: Bot):
        self.s = session
        self.bot = bot

    # ---------- выдача инвайтов ----------

    async def create_one_time_link(
        self,
        tg_user_id: int,
        chat_id: int,
        ttl_minutes: int = 60,
        access_days: Optional[int] = None,
    ) -> str:
        """
        Создаёт одноразовую ссылку в конкретный чат/канал и фиксирует её в БД.
        access_days: если задано, запишем срок действия доступа (для автокика)
        """
        expire_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        link: ChatInviteLink = await self.bot.create_chat_invite_link(
            chat_id=chat_id,
            expire_date=expire_at,
            member_limit=1,
            creates_join_request=False,
        )

        values = dict(
            tg_user_id=tg_user_id,
            chat_id=chat_id,
            invite_link=link.invite_link,
            invite_expires_at=expire_at,
            used=False,
            access_expires_at=(
                datetime.utcnow() + timedelta(days=access_days)
                if access_days
                else None
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await self.s.execute(insert(AccessGrant).values(**values))
        await self.s.commit()

        return link.invite_link

    async def grant_both_links(
        self,
        tg_user_id: int,
        channel_id: int,
        group_id: int,
        ttl_minutes: int = 60,
        access_days: Optional[int] = None,
    ) -> tuple[str, str]:
        """
        Удобная обёртка: сразу выдаёт 2 ссылки (канал + группа),
        обе записывает в БД.
        """
        ch = await self.create_one_time_link(
            tg_user_id=tg_user_id,
            chat_id=channel_id,
            ttl_minutes=ttl_minutes,
            access_days=access_days,
        )
        gr = await self.create_one_time_link(
            tg_user_id=tg_user_id,
            chat_id=group_id,
            ttl_minutes=ttl_minutes,
            access_days=access_days,
        )
        return ch, gr

    # ---------- поиск свежей неиспользованной ссылки (реюз) ----------

    async def get_unexpired_link(
        self,
        tg_user_id: int,
        chat_id: int,
        min_ttl_minutes: int = 5,
    ) -> str | None:
        """
        Найти свежую неиспользованную ссылку, у которой до истечения осталось >= min_ttl_minutes.
        Нужна, чтобы не плодить новые инвайты при спаме «Проверить оплату».
        """
        now = datetime.utcnow()
        min_expire = now + timedelta(minutes=min_ttl_minutes)

        q = (
            select(AccessGrant.invite_link, AccessGrant.invite_expires_at)
            .where(
                AccessGrant.tg_user_id == tg_user_id,
                AccessGrant.chat_id == chat_id,
                AccessGrant.used.is_(False),
                AccessGrant.invite_expires_at.is_not(None),
                AccessGrant.invite_expires_at > min_expire,
            )
            .order_by(AccessGrant.invite_expires_at.desc())
            .limit(1)
        )
        res = await self.s.execute(q)
        row = res.first()
        return row[0] if row else None

    # ---------- отметка «использовано» ----------

    async def mark_used(self, tg_user_id: int, chat_id: int, invite_link: str) -> None:
        await self.s.execute(
            update(AccessGrant)
            .where(
                AccessGrant.tg_user_id == tg_user_id,
                AccessGrant.chat_id == chat_id,
                AccessGrant.invite_link == invite_link,
                AccessGrant.used.is_(False),
            )
            .values(used=True, updated_at=datetime.utcnow())
        )
        await self.s.commit()

    # ---------- проверки членства ----------

    async def is_member(self, chat_id: int, user_id: int) -> bool:
        try:
            cm: ChatMember = await self.bot.get_chat_member(chat_id, user_id)
            return cm.status in {"member", "administrator", "creator"}
        except TelegramBadRequest:
            return False

    # ---------- отзыв доступа (кик) ----------

    async def revoke_access(self, chat_id: int, user_id: int) -> bool:
        """
        Кик + разблок, чтобы юзер мог снова войти при новой оплате.
        Возвращает True, если попытались кикнуть (даже если он уже не в чате).
        """
        try:
            await self.bot.ban_chat_member(chat_id, user_id)
            await self.bot.unban_chat_member(chat_id, user_id)
            return True
        except TelegramBadRequest:
            # нет прав, или уже не участник — для MVP ок
            return False

    # ---------- выборки для фоновых задач ----------

    async def get_expired_accesses(self) -> list[AccessGrant]:
        """
        Все записи, у которых access_expires_at прошёл.
        """
        now = datetime.utcnow()
        q = (
            select(AccessGrant)
            .where(AccessGrant.access_expires_at.is_not(None))
            .where(AccessGrant.access_expires_at < now)
        )
        res = await self.s.execute(q)
        return list(res.scalars())

    async def purge_by_user(self, tg_user_id: int) -> int:
        """
        Удалить все записи access_grants пользователя (после отзыва доступа).
        Возвращает число удалённых строк.
        """
        res = await self.s.execute(
            delete(AccessGrant).where(AccessGrant.tg_user_id == tg_user_id)
        )
        await self.s.commit()
        return res.rowcount or 0
