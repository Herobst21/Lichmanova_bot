import logging
from sqlalchemy.exc import PendingRollbackError
from app.utils.dates import now_utc

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self, session, repo):
        self.s = session
        self.repo = repo

    async def tick(self) -> None:
        """Периодическая задача: ищем просроченные напоминания и рассылаем их."""
        now = now_utc()
        due = await self.repo.due(now)
        for item in due:
            await self._process(item)