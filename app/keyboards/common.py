from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import KeyboardButton

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="Бесплатные материалы"))
    kb.row(KeyboardButton(text="FAQ"), KeyboardButton(text="Поддержка"))
    return kb.as_markup(resize_keyboard=True)
