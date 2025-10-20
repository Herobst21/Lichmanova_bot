from aiogram import Router
from aiogram.types import ErrorEvent
import logging

router = Router()

@router.error()
async def on_error(event: ErrorEvent):
    logging.exception("Error in handler: %s", event.exception)
