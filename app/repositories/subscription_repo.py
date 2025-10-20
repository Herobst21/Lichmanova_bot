from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SubscriptionRepo:
    def __init__(self, s: AsyncSession) -> None:
        self.s = s
        self.model = Subscription

    async def current_for_user(self, user_id: int) -> Optional[Subscription]:
        q = await self.s.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        return q.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: int,
        plan: str,
        expires_at: datetime,
        status: str = "active",
        is_trial: bool = False,
        auto_renew: bool = False,
    ) -> Subscription:
        sub = Subscription(
            user_id=user_id,
            plan=plan,
            started_at=now_utc(),
            expires_at=expires_at,
            status=status,
            is_trial=is_trial,
            auto_renew=auto_renew,
        )
        self.s.add(sub)
        await self.s.commit()
        await self.s.refresh(sub)
        return sub

    async def create_or_extend(
        self,
        *,
        user_id: int,
        plan: str,
        new_expires_at: datetime,
        is_trial: bool,
        auto_renew: bool,
    ) -> Subscription:
        cur = await self.current_for_user(user_id)
        if cur and cur.expires_at > now_utc() and cur.status == "active":
            cur.plan = plan
            cur.started_at = now_utc()
            cur.expires_at = new_expires_at
            cur.is_trial = is_trial
            cur.auto_renew = auto_renew
            await self.s.commit()
            await self.s.refresh(cur)
            return cur

        return await self.create(
            user_id=user_id,
            plan=plan,
            expires_at=new_expires_at,
            status="active",
            is_trial=is_trial,
            auto_renew=auto_renew,
        )

    async def has_active_by_tg(self, tg_user_id: int) -> bool:
        """
        Проверка активной подписки по Telegram ID.
        """
        q = await self.s.execute(
            select(Subscription.id)
            .join(User, User.id == Subscription.user_id)
            .where(User.tg_id == tg_user_id)
            .where(Subscription.status == "active")
            .where(Subscription.expires_at > now_utc())
            .limit(1)
        )
        return q.scalar_one_or_none() is not None
