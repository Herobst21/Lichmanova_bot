from app.repositories.material_repo import MaterialRepo
class MaterialService:
    def __init__(self, repo: MaterialRepo): self.repo = repo
    async def list(self): return await self.repo.list()
