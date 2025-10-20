from __future__ import annotations

import os
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.client.bot import Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message

from app.db import SessionLocal
from app.services.payment_service import PaymentService
from app.services.access_service import AccessService
from app.pay.robokassa import build_payment_link
from app.config import settings

CONTENT_CHANNEL_ID = int(os.getenv("CONTENT_CHANNEL_ID"))
CONTENT_CHAT_ID = int(os.getenv("CONTENT_CHAT_ID"))

# Срок действия доступа по планам (дни)
PLAN_ACCESS_DAYS = {
    "m1": 30,
    "m3": 90,
    "m6": 180,
    "trial3_10": 3,
}

router = Router()


# ---------- утилиты цен ----------
def _price_for_plan(plan: str) -> int:
    if plan == "trial3_10":
        return int(getattr(settings, "TRIAL_PRICE", 10))
    price_map: dict[str, int] = {}
    for pair in str(getattr(settings, "PLAN_PRICES_RUB", "")).split(","):
        pair = pair.strip()
        if not pair:
            continue
        try:
            k, v = pair.split(":")
            price_map[k.strip()] = int(v.strip())
        except ValueError:
            continue
    return price_map.get(plan, price_map.get("m1", 990))

# Совместимость со старым кодом: age_verify ожидает МАПУ цен
PRICE_RUB = {
    "m1": _price_for_plan("m1"),
    "m3": _price_for_plan("m3"),
    "m6": _price_for_plan("m6"),
    "trial3_10": _price_for_plan("trial3_10"),
}

# Нормальное имя для прямого вызова из кода
def price_for_plan(plan: str) -> int:
    return _price_for_plan(plan)



# ---------- подписи и тексты ----------
def _label(plan: str) -> str:
    mapping = {
        "m1": "1 месяц — ",
        "m3": "3 месяца — ",
        "m6": "6 месяцев — ",
        "trial3_10": "Пробный доступ — 3 дня — ",
    }
    return f"{mapping[plan]}{_fmt_rub(_price_for_plan(plan))}"


def _tariffs_text() -> str:
    return (
        "🧾 <b>Оформить подписку</b>\n\n"
        "👉 Тарифы:\n"
        f"• 1 месяц — {_fmt_rub(_price_for_plan('m1'))}\n"
        f"• 3 месяца — {_fmt_rub(_price_for_plan('m3'))}\n"
        f"• 6 месяцев — {_fmt_rub(_price_for_plan('m6'))}\n\n"
        "Подписка — регулярная (автопродление можно отключить в любой момент).\n"
        "Если тебе нет 18 лет — действует скидка 25%.\n"
    )


def tariffs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_label("m1"), callback_data="tariff:m1")],
        [InlineKeyboardButton(text=_label("m3"), callback_data="tariff:m3")],
        [InlineKeyboardButton(text=_label("m6"), callback_data="tariff:m6")],
        [InlineKeyboardButton(text="Мне нет 18 лет", callback_data="u18_start")],
    ])


def back_to_tariffs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к тарифам", callback_data="open_tariffs")]
    ])


def pay_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],
        [InlineKeyboardButton(text="⬅️ Назад к тарифам", callback_data="open_tariffs")],
    ])


# ---------- общий вход в меню тарифов ----------
@router.callback_query(F.data == "open_tariffs")
async def open_tariffs(call: CallbackQuery):
    await call.message.answer(_tariffs_text(), reply_markup=tariffs_kb())
    await call.answer()


@router.message(F.text.lower().contains("оформить подписку"))
async def open_tariffs_from_text(msg: Message):
    await msg.answer(_tariffs_text(), reply_markup=tariffs_kb())


# ---------- согласие на рекуррент ----------
CONSENT_TEXT = (
    "✅ Я даю согласие на регулярные списания, на обработку персональных данных "
    "и принимаю условия публичной оферты."
)


def _period_days(plan: str) -> int:
    return {"m1": 30, "m3": 90, "m6": 180}[plan]


def consent_text(plan: str) -> str:
    price = _price_for_plan(plan)
    return (
        f"🎟 <b>Подписка на { {'m1':'1 месяц','m3':'3 месяца','m6':'6 месяцев'}[plan] }</b>\n"
        f"Сумма: <b>{_fmt_rub(price)}</b>\n"
        f"Периодичность списаний: раз в {_period_days(plan)} дней.\n\n"
        f"{CONSENT_TEXT}\n"
        f"С условиями можно ознакомиться тут: "
        f"<a href='{getattr(settings,'OFFERTA_URL','https://example.com/offer')}'>Оферта</a> и "
        f"<a href='{getattr(settings,'PRIVACY_URL','https://example.com/privacy')}'>Политика</a>."
    )



def consent_kb(plan: str, agreed: bool) -> InlineKeyboardMarkup:
    box = "☑" if agreed else "☐"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{box} Я согласен", callback_data=f"consent:toggle:{plan}")],
        [InlineKeyboardButton(
            text="Продолжить к оплате" if agreed else "Продолжить к оплате (недоступно)",
            callback_data=f"consent:confirm:{plan}"
        )],
        [InlineKeyboardButton(text="⬅️ Назад к тарифам", callback_data="open_tariffs")],
    ])


# ---------- карточка тарифа ----------
def card_text(plan: str) -> str:
    base = {
        "m1": "🎟 <b>Подписка на 1 месяц</b>",
        "m3": "🎟 <b>Подписка на 3 месяца</b>",
        "m6": "🎟 <b>Подписка на 6 месяцев</b>",
        "trial3_10": "🎁 <b>Пробный доступ</b> — 3 дня",
    }[plan]
    policy = (
        "\n\nНажимая «Оплатить», ты подтверждаешь согласие с "
        f"<a href='{getattr(settings,'PRIVACY_URL','https://example.com/privacy')}'>Политикой конфиденциальности</a> "
        f"и <a href='{getattr(settings,'OFFERTA_URL','https://example.com/offer')}'>Публичной офертой</a>."
    )
    return f"{base}\nЦена: {_fmt_rub(_price_for_plan(plan))}{policy}"


@router.callback_query(F.data.startswith("tariff:"))
async def show_tariff_or_info(call: CallbackQuery):
    plan = call.data.split(":", 1)[1]

    # инфо по u18
    if plan == "u18_info":
        await call.message.answer(
            "🔖 Скидка 25% для пользователей младше 18 лет подключается через верификацию.",
            reply_markup=back_to_tariffs_kb(),
        )
        await call.answer()
        return

    # обычные планы — сначала экран согласия (далее обработает age_verify)
    if plan in ("m1", "m3", "m6"):
        await call.message.answer(consent_text(plan), reply_markup=consent_kb(plan, False))
        await call.answer()
        return

    # прочее (например, trial) — разовый платёж
    async with SessionLocal() as session:
        svc = PaymentService(session)

        # Robokassa требует числовой InvId; делаем уникальный 32-битный
        from uuid import uuid4
        inv_id = int(uuid4().hex[:8], 16)

        # создаём инвойс с provider_invoice_id равным InvId (чтобы вебхук/поиск сошлись)
        payment, invoice_id = await svc.create_invoice(
            tg_user_id=call.from_user.id,
            plan=plan,
            provider_invoice_id=str(inv_id),
        )

        pay_url = build_payment_link(
            amount_rub=float(_price_for_plan(plan)),
            inv_id=inv_id,
            user_id=call.from_user.id,
            description=f"Подписка {plan}",
        )

    await call.message.answer(card_text(plan), reply_markup=pay_kb(pay_url))
    await call.answer()


# ---------- проверка оплаты ----------
@router.callback_query(F.data == "check_payment")
async def check_payment(call: CallbackQuery, bot: Bot):
    async with SessionLocal() as session:
        pay = PaymentService(session)

        # 1) есть ли активная подписка
        if not await pay.user_has_active_subscription(call.from_user.id):
            await call.message.answer("⏳ Оплата ещё не подтвердилась. Попробуй через минуту.")
            await call.answer()
            return

        # 2) проверяем членство
        access = AccessService(session, bot)
        in_channel = await access.is_member(CONTENT_CHANNEL_ID, call.from_user.id)
        in_group = await access.is_member(CONTENT_CHAT_ID, call.from_user.id)

        if in_channel and in_group:
            await call.message.answer("✅ Доступ уже активен: ты состоишь и в канале, и в чате.")
            await call.answer()
            return

        # 3) срок доступа по плану
        sub = await pay.get_active_subscription(call.from_user.id)
        plan = getattr(sub, "plan", "m1")
        access_days = PLAN_ACCESS_DAYS.get(plan, 30)

        # 4) пробуем реюзнуть живые ссылки, иначе генерим новые и пишем в БД
        links: list[str] = []
        reuse_window_min = 5

        if not in_channel:
            old_ch = await access.get_unexpired_link(call.from_user.id, CONTENT_CHANNEL_ID, reuse_window_min)
            if old_ch:
                links.append(f"Канал: {old_ch}")
            else:
                ch_new = await access.create_one_time_link(
                    tg_user_id=call.from_user.id,
                    chat_id=CONTENT_CHANNEL_ID,
                    ttl_minutes=60,
                    access_days=access_days,
                )
                links.append(f"Канал: {ch_new}")

        if not in_group:
            old_gr = await access.get_unexpired_link(call.from_user.id, CONTENT_CHAT_ID, reuse_window_min)
            if old_gr:
                links.append(f"Чат: {old_gr}")
            else:
                gr_new = await access.create_one_time_link(
                    tg_user_id=call.from_user.id,
                    chat_id=CONTENT_CHAT_ID,
                    ttl_minutes=60,
                    access_days=access_days,
                )
                links.append(f"Чат: {gr_new}")

        # 5) сообщение пользователю
        if links:
            await call.message.answer(
                "✅ Оплата подтверждена.\n\n"
                + "\n".join(links)
                + "\n\nСсылки одноразовые и действуют 60 минут."
            )
        else:
            await call.message.answer("✅ Доступ активен.")

    await call.answer()
