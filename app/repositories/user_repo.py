from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.s = session

    async def get_by_tg_id(self, tg_id: int):
        q = await self.s.execute(select(User).where(User.tg_id == tg_id))
        return q.scalar_one_or_none()

    async def create_from_tg(self, tg_user) -> User:
        u = User(
            tg_id=tg_user.id,
            username=getattr(tg_user, "username", None),
            first_name=getattr(tg_user, "first_name", None),
            last_name=getattr(tg_user, "last_name", None),
        )
        self.s.add(u)
        await self.s.commit()
        await self.s.refresh(u)
        return u

    async def get_or_create_by_tg_id(self, tg_id: int, **kwargs) -> User:
        u = await self.get_by_tg_id(tg_id)
        if u:
            return u
        class TG:  # адаптер под create_from_tg
            id = tg_id
            username = None
            first_name = None
            last_name = None
        return await self.create_from_tg(TG())


UserRepo = UserRepository
__all__ = ["UserRepository", "UserRepo"]
