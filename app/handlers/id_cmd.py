from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("id"))
async def show_id(msg: Message):
    await msg.answer(f"Ваш Telegram ID: {msg.from_user.id}")
