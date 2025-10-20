from aiogram import Router, F
from aiogram.types import Message
from app.config import settings

router = Router()

@router.message(F.text == "/admin")
async def admin_root(m: Message):
    if m.from_user.id != settings.OWNER_ID:
        await m.answer("Нет доступа.")
        return
    await m.answer("Админ-панель: скоро тут будет управление.")

@router.message(F.text.startswith("/fake_paid"))
async def fake_paid_cmd(m: Message, payments):
    """
    /fake_paid <provider_invoice_id>
    Подтверждаем фейковую оплату и активируем/продлеваем подписку.
    Доступно только админам.
    """
    # защита по админам
    admins = set(map(int, settings.ADMINS))
    if m.from_user.id not in admins:
        return await m.reply("Недостаточно прав.")

    parts = m.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return await m.reply("Укажи invoice_id: /fake_paid <provider_invoice_id>")

    invoice_id = parts[1].strip()
    try:
        sub = await payments.confirm_payment(invoice_id)
        return await m.reply(
            "Оплата подтверждена ✅\n"
            f"План: <b>{sub.plan}</b>\n"
            f"Действует до: <b>{sub.expires_at:%Y-%m-%d %H:%M:%S %Z}</b>"
        )
    except Exception as e:
        return await m.reply(f"Не удалось подтвердить: {e}")