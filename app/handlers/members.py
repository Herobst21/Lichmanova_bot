# app/handlers/members.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION

from aiogram.client.bot import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.services.access_service import AccessService

router = Router(name="members")

# Ловим вступление в канал/группу по пригласительной ссылке
@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
)
async def on_member_join(event: ChatMemberUpdated, bot: Bot):
    """
    Если юзер зашёл по нашей ссылке, Telegram положит её в event.invite_link.
    Помечаем запись в access_grants как used=True.
    """
    invite = event.invite_link
    if not invite:
        return  # зашёл не по ссылке или кинул кто-то другой

    user_id = event.from_user.id
    chat_id = event.chat.id
    link = invite.invite_link

    async with SessionLocal() as session:  # type: AsyncSession
        svc = AccessService(session, bot)
        await svc.mark_used(tg_user_id=user_id, chat_id=chat_id, invite_link=link)
