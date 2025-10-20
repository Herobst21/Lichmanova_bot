from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings


def _price_map() -> dict[str, int]:
    result = {}
    for p in settings.PLAN_PRICES_RUB.split(","):
        try:
            k, v = [x.strip() for x in p.split(":")]
            result[k] = int(v)
        except Exception:
            continue
    return result


def plans_keyboard(show_trial: bool = True) -> InlineKeyboardMarkup:
    m = _price_map()
    buttons = []
    if show_trial and getattr(settings, "TRIAL_ENABLED", True) and getattr(settings, "TRIAL_MODE", "paid") == "paid":
        buttons.append([InlineKeyboardButton(text="Три дня за 10 ₽", callback_data="plan:trial3_10")])
    for plan in ("m1", "m3", "m6"):
        if plan in m:
            months = {"m1": "1 месяц", "m3": "3 месяца", "m6": "6 месяцев"}[plan]
            buttons.append([
                InlineKeyboardButton(
                    text=f"{months} — {m[plan]:,} ₽".replace(",", " "),
                    callback_data=f"plan:{plan}"
                )
            ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pay_button_url(invoice_id: str) -> InlineKeyboardMarkup:
    url = f"{settings.PUBLIC_BASE_URL}/payments/fake/pay?invoice_id={invoice_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить", url=url)]
    ])


def pay_button_fake_cb(invoice_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить (фейк)", callback_data=f"fakepay:{invoice_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ])


def trial_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить 10 ₽", callback_data="plan:trial3_10")],
    ])
