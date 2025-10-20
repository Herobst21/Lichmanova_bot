from app.repositories.churn_repo import ChurnRepo
class ChurnService:
    def __init__(self, repo: ChurnRepo): self.repo = repo
    async def save(self, user_id: int, code: str, text: str | None):
        return await self.repo.save(user_id, code, text)
