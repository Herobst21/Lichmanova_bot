# app/handlers/start.py
from pathlib import Path

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

router = Router()

WELCOME_TEXT = (
    "🏆 Привет, Чемпион!\n\n"
    "Ты у входа в Эпоху Роста — экосистему, где спортивное мышление, уверенность и результаты "
    "собираются в одну рабочую систему.\n\n"
    "🔥 Что внутри:\n"
    "1) База знаний и упражнения — ломаем старые установки.\n"
    "2) Эфиры с профи — разборы с чемпионами и экспертами.\n"
    "3) Сообщество — окружение, которое не даёт стоять на месте.\n"
    "4) Проект внутри клуба — ритуалы, привычки и восстановление.\n\n"
    "🎯 Миссия: дать каждому спортсмену инструменты победителя. Без стресса. Со смыслом.\n\n"
    "⏳ Пора действовать. Врывайся в Эпоху Роста."
)

def _welcome_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оформить подписку на клуб", callback_data="open_tariffs")],
        [InlineKeyboardButton(text="Получить пробный период", callback_data="tariff:trial3_10")],
    ])

# Картинка лежит тут: app/assets/ЭПОХА (5).png
BANNER_PATH = Path(__file__).resolve().parents[1] / "assets" / "ЭПОХА (5).png"

@router.message(CommandStart())
async def start(message: Message) -> None:
    if BANNER_PATH.exists():
        photo = FSInputFile(BANNER_PATH)
        await message.answer_photo(photo=photo, caption=WELCOME_TEXT, reply_markup=_welcome_kb())
    else:
        await message.answer(WELCOME_TEXT, reply_markup=_welcome_kb())
