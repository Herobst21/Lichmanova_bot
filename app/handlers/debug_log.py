from aiogram import Router, F
from aiogram.types import Message
import logging
router = Router()
@router.message(F.text)
async def dbg_log(m: Message):
    logging.warning("DBG: text=%r tg_id=%s", m.text, m.from_user.id)
