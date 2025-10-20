from sqlalchemy.ext.asyncio import AsyncSession
from app.models.access_link import AccessLink

class AccessRepo:
    def __init__(self, s: AsyncSession): self.s = s
    async def save(self, user_id: int, channel_id: int | None, chat_id: int | None, invite_link: str | None) -> AccessLink:
        al = AccessLink(user_id=user_id, channel_id=channel_id, chat_id=chat_id, invite_link=invite_link)
        self.s.add(al); await self.s.commit(); await self.s.refresh(al); return al
