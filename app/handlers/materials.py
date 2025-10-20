from aiogram import Router, F
from aiogram.types import Message
from app.services.material_service import MaterialService

router = Router()

@router.message(F.text == "Бесплатные материалы")
async def list_materials(m: Message, materials: MaterialService):
    items = await materials.list()
    if not items:
        await m.answer("Пока пусто. Скоро добавим.")
        return
    text = "\n".join([f"• <b>{x.title}</b> — {x.description or ''}" for x in items])
    await m.answer(text or "Пусто")
