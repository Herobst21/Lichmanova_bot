from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.material import Material

class MaterialRepo:
    def __init__(self, s: AsyncSession): self.s = s
    async def list(self) -> list[Material]:
        q = await self.s.execute(select(Material).order_by(Material.created_at.desc()))
        return list(q.scalars().all())
