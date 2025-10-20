from aiogram import Router, F
from aiogram.types import Message
from app.config import settings
from app.services.subscription_service import SubscriptionService

router = Router()

@router.message(F.text == "Три дня бесплатно")
async def trial(m: Message, subs: SubscriptionService):
    if not settings.TRIAL_ENABLED:
        await m.answer("Триал отключен.")
        return
    await subs.activate(m.from_user.id, "m1", days=settings.TRIAL_DAYS, is_trial=True)
    await m.answer("Триал активирован. Нажми 'Вступить в чат'.")
