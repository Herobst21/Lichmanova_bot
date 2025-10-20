from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.setting import Setting

class SettingRepo:
    def __init__(self, s: AsyncSession): self.s = s
    async def get(self, key: str) -> str | None:
        q = await self.s.execute(select(Setting).where(Setting.key==key))
        row = q.scalar_one_or_none()
        return row.value if row else None
    async def set(self, key: str, value: str) -> None:
        v = await self.s.execute(select(Setting).where(Setting.key==key))
        row = v.scalar_one_or_none()
        if row:
            row.value = value
        else:
            self.s.add(Setting(key=key, value=value))
        await self.s.commit()
