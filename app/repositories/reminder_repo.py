from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from app.models.reminder import Reminder

class ReminderRepo:
    def __init__(self, s: AsyncSession):
        self.s = s

    async def create(self, user_id: int, kind: str, due_at) -> Reminder:
        r = Reminder(user_id=user_id, kind=kind, due_at=due_at)
        self.s.add(r)
        await self.s.commit()
        await self.s.refresh(r)
        return r

    async def due(self, now):
        q = await self.s.execute(
            select(Reminder).where(Reminder.sent_at.is_(None), Reminder.due_at <= now)
        )
        return q.scalars().all()

    async def mark_sent(self, rid: int):
        ts = datetime.now(timezone.utc)
        await self.s.execute(
            update(Reminder).where(Reminder.id == rid).values(sent_at=ts)
        )
        await self.s.commit()
