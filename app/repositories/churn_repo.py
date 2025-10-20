from sqlalchemy.ext.asyncio import AsyncSession
from app.models.churn_reason import ChurnReason

class ChurnRepo:
    def __init__(self, s: AsyncSession): self.s = s
    async def save(self, user_id: int, code: str, text: str | None) -> ChurnReason:
        c = ChurnReason(user_id=user_id, reason_code=code, reason_text=text)
        self.s.add(c); await self.s.commit(); await self.s.refresh(c); return c
