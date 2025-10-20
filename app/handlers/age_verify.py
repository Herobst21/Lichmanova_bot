from __future__ import annotations

import logging
import secrets
from typing import Optional, Dict

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text as sql_text

from app.config import settings
from app.db import get_session
from app.services.payment_service import PaymentService
from app.pay.robokassa import build_payment_link
from app.handlers.pay import PRICE_RUB, pay_kb  # reuse цен и кнопок

router = Router()
logger = logging.getLogger(__name__)

# ---------- CONFIG ----------
def _admin_chat_id() -> Optional[int]:
    if getattr(settings, "AGE_VERIFY_ADMIN_ID", None):
        return settings.AGE_VERIFY_ADMIN_ID
    if getattr(settings, "OWNER_ID", None):
        return settings.OWNER_ID
    admins = getattr(settings, "ADMINS", []) or []
    return admins[0] if admins else None

SUPPORT_URL: str = getattr(settings, "SUPPORT_URL", "https://t.me/your_support_here")

# in-memory для MVP (на проде лучше хранить в БД)
VERIFIED_USERS: set[int] = set()
PENDING: Dict[str, Dict] = {}  # token -> {"user_id": int, "file_id": str}

BASE_TO_U18 = {"m1": "m1_u18", "m3": "m3_u18", "m6": "m6_u18"}

PRICE_RUB_U18: Dict[str, int] = {
    "m1_u18": int(round(PRICE_RUB["m1"] * 0.75)),
    "m3_u18": int(round(PRICE_RUB["m3"] * 0.75)),
    "m6_u18": int(round(PRICE_RUB["m6"] * 0.75)),
}
LABEL_U18: Dict[str, str] = {
    "m1_u18": f"1 месяц −25% — {PRICE_RUB_U18['m1_u18']} ₽",
    "m3_u18": f"3 месяца −25% — {PRICE_RUB_U18['m3_u18']} ₽",
    "m6_u18": f"6 месяцев −25% — {PRICE_RUB_U18['m6_u18']} ₽",
}

POLICY_HTML = (
    "\n\nНажимая «Оплатить», ты подтверждаешь согласие с "
    f"<a href='{getattr(settings,'PRIVACY_URL','https://example.com/privacy')}'>Политикой конфиденциальности</a> "
    f"и <a href='{getattr(settings,'OFFERTA_URL','https://example.com/offer')}'>Публичной офертой</a>."
)

CONSENT_TEXT = (
    "✅ Я даю согласие на регулярные списания, на обработку персональных данных "
    "и принимаю условия публичной оферты."
)

# ---------- FSM ----------
class AgeCheck(StatesGroup):
    waiting_photo = State()

# ---------- UI ----------
def kb_u18_intro() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Поддержка", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="← Назад к тарифам", callback_data="open_tariffs")],
    ])

def kb_admin_decision(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"age:approve:{token}"),
            InlineKeyboardButton(text="⛔ Отклонить", callback_data=f"age:reject:{token}"),
        ]
    ])

def kb_u18_discount_plans() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LABEL_U18["m1_u18"], callback_data="u18:tariff:m1_u18")],
        [InlineKeyboardButton(text=LABEL_U18["m3_u18"], callback_data="u18:tariff:m3_u18")],
        [InlineKeyboardButton(text=LABEL_U18["m6_u18"], callback_data="u18:tariff:m6_u18")],
        [InlineKeyboardButton(text="← Назад к тарифам", callback_data="open_tariffs")],
    ])

def consent_kb(plan_code: str, agreed: bool) -> InlineKeyboardMarkup:
    box = "☑" if agreed else "☐"
    rows = [
        [InlineKeyboardButton(text=f"{box} Я согласен", callback_data=f"consent:toggle:{plan_code}")],
        [InlineKeyboardButton(
            text="Продолжить к оплате" if agreed else "Продолжить к оплате (недоступно)",
            callback_data=f"consent:confirm:{plan_code}"
        )],
        [InlineKeyboardButton(text="← Назад к тарифам", callback_data="open_tariffs")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ---------- HELPERS ----------
def _user_mention(user_id: int, full_name: str) -> str:
    return f"<a href='tg://user?id={user_id}'>{full_name}</a>"

def card_text_u18(plan_code: str) -> str:
    title = {
        "m1_u18": "🎟 <b>Подписка на 1 месяц</b> — скидка 25%",
        "m3_u18": "🎟 <b>Подписка на 3 месяца</b> — скидка 25%",
        "m6_u18": "🎟 <b>Подписка на 6 месяцев</b> — скидка 25%",
    }[plan_code]
    price = PRICE_RUB_U18[plan_code]
    return f"{title}\nЦена: {price} ₽{POLICY_HTML}"

def plan_period_days(plan_code: str) -> int:
    base = plan_code.replace("_u18", "")
    return {"m1": 30, "m3": 90, "m6": 180}[base]

def plan_amount(plan_code: str) -> int:
    return PRICE_RUB_U18[plan_code] if plan_code.endswith("_u18") else PRICE_RUB[plan_code]

async def save_consent(session: AsyncSession, *, user_id: int, plan: str, price_rub: int, period_days: int) -> None:
    # без миграций: создаём таблицу, если её нет
    await session.execute(sql_text("""
    CREATE TABLE IF NOT EXISTS consent_logs (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        plan VARCHAR(32) NOT NULL,
        price_rub INTEGER NOT NULL,
        period_days INTEGER NOT NULL,
        consent_text TEXT NOT NULL,
        offer_url VARCHAR(255) NOT NULL,
        privacy_url VARCHAR(255) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """))
    await session.execute(sql_text("""
        INSERT INTO consent_logs (user_id, plan, price_rub, period_days, consent_text, offer_url, privacy_url)
        VALUES (:user_id, :plan, :price_rub, :period_days, :consent_text, :offer_url, :privacy_url)
    """), {
        "user_id": user_id,
        "plan": plan,
        "price_rub": price_rub,
        "period_days": period_days,
        "consent_text": CONSENT_TEXT,
        "offer_url": getattr(settings, "OFFERTA_URL", "https://example.com/offer"),
        "privacy_url": getattr(settings, "PRIVACY_URL", "https://example.com/privacy"),
    })
    await session.commit()

# ---------- U18 ENTRY ----------
@router.callback_query(F.data == "u18_start")
async def u18_start(call: CallbackQuery, state: FSMContext):
    text = (
        "Нужна верификация возраста.\n\n"
        "Пришли <b>фото паспорта</b> (можно закрыть серию и номер). "
        "Должны быть видны <b>ФИО</b> и <b>дата рождения</b>.\n\n"
        "Если остались вопросы — «Поддержка». Или «Назад», если передумал."
    )
    await state.set_state(AgeCheck.waiting_photo)
    try:
        await call.message.edit_text(text, reply_markup=kb_u18_intro())
    except Exception:
        await call.message.answer(text, reply_markup=kb_u18_intro())
    await call.answer()

# ---------- ПРИЁМ ПАСПОРТА ----------
@router.message(AgeCheck.waiting_photo, F.photo)
async def u18_got_passport(msg: Message, state: FSMContext):
    admin_id = _admin_chat_id()
    if not admin_id:
        await msg.answer("Техническая ошибка: не настроен чат модерации. Сообщи администратору.")
        return

    file_id = msg.photo[-1].file_id
    user = msg.from_user
    token = secrets.token_urlsafe(16)
    PENDING[token] = {"user_id": user.id, "file_id": file_id}

    caption = (
        "<b>Верификация возраста</b>\n\n"
        f"Пользователь: {_user_mention(user.id, user.full_name)}\n"
        f"Username: @{user.username or '—'}\n"
        f"User ID: <code>{user.id}</code>\n\n"
        "Проверь паспорт и выбери действие:"
    )

    try:
        await msg.bot.send_photo(
            chat_id=admin_id,
            photo=file_id,
            caption=caption,
            reply_markup=kb_admin_decision(token),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("Не смог отправить фото админу: %s", e)
        await msg.answer("Не получилось отправить на модерацию. Попробуй ещё раз позже.")
        return

    await state.clear()
    await msg.answer("Документ отправлен на проверку. Обычно это недолго.")

@router.message(AgeCheck.waiting_photo)
async def u18_need_photo(msg: Message, state: FSMContext):
    await msg.answer("Это не похоже на фото. Отправь именно <b>фотографию</b> паспорта.", parse_mode="HTML")

# ---------- РЕШЕНИЕ АДМИНА ----------
@router.callback_query(F.data.startswith("age:approve:"))
async def age_approve(call: CallbackQuery):
    token = call.data.split(":", 2)[-1]
    info = PENDING.pop(token, None)
    if not info:
        await call.answer("Заявка уже обработана или устарела.", show_alert=True)
        return

    user_id = info["user_id"]
    VERIFIED_USERS.add(user_id)

    try:
        await call.bot.send_message(
            chat_id=user_id,
            text=(
                "Возраст подтвержден. Доступна <b>скидка −25%</b> на подписку.\n"
                "Выбери тариф:"
            ),
            parse_mode="HTML",
            reply_markup=kb_u18_discount_plans(),
        )
    except Exception as e:
        logger.exception("Не смог уведомить пользователя: %s", e)

    try:
        await call.message.edit_caption(
            caption=(call.message.caption or "") + "\n\n✅ Одобрено.",
            reply_markup=None,
        )
    except Exception:
        pass

    await call.answer("Подтверждено.")

@router.callback_query(F.data.startswith("age:reject:"))
async def age_reject(call: CallbackQuery):
    token = call.data.split(":", 2)[-1]
    info = PENDING.pop(token, None)
    if not info:
        await call.answer("Заявка уже обработана или устарела.", show_alert=True)
        return

    user_id = info["user_id"]
    try:
        await call.bot.send_message(
            chat_id=user_id,
            text="Увы, верификация отклонена. Возвращаю к тарифам.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к тарифам", callback_data="open_tariffs")]
            ])
        )
    except Exception as e:
        logger.exception("Не смог уведомить пользователя: %s", e)

    try:
        await call.message.edit_caption(
            caption=(call.message.caption or "") + "\n\n⛔ Отклонено.",
            reply_markup=None,
        )
    except Exception:
        pass

    await call.answer("Отклонено.")

# ---------- СОГЛАСИЕ ----------
CONSENT_STATE: Dict[int, Dict[str, bool]] = {}  # user_id -> {plan_code: agreed}

def consent_text(plan_code: str) -> str:
    price = plan_amount(plan_code)
    period = plan_period_days(plan_code)
    base = plan_code.replace("_u18", "")
    title = {
        "m1": "Подписка на 1 месяц",
        "m3": "Подписка на 3 месяца",
        "m6": "Подписка на 6 месяцев",
    }[base]
    suffix = " — скидка 25%" if plan_code.endswith("_u18") else ""
    return (
        f"🎟 <b>{title}{suffix}</b>\n"
        f"Сумма: <b>{price} ₽</b>\n"
        f"Периодичность списаний: раз в {period} дней.\n\n"
        f"{CONSENT_TEXT}\n"
        f"С условиями можно ознакомиться тут: "
        f"<a href='{getattr(settings,'OFFERTA_URL','https://example.com/offer')}'>Оферта</a> и "
        f"<a href='{getattr(settings,'PRIVACY_URL','https://example.com/privacy')}'>Политика</a>."
    )

@router.callback_query(F.data.startswith("consent:toggle:"))
async def consent_toggle(call: CallbackQuery):
    plan = call.data.split(":", 2)[-1]
    uid = call.from_user.id
    CONSENT_STATE.setdefault(uid, {})
    current = CONSENT_STATE[uid].get(plan, False)
    CONSENT_STATE[uid][plan] = not current
    try:
        await call.message.edit_reply_markup(reply_markup=consent_kb(plan, CONSENT_STATE[uid][plan]))
    except Exception:
        pass
    await call.answer()

@router.callback_query(F.data.startswith("consent:confirm:"))
async def consent_confirm(call: CallbackQuery, session: AsyncSession = get_session()):
    plan = call.data.split(":", 2)[-1]
    uid = call.from_user.id
    agreed = CONSENT_STATE.get(uid, {}).get(plan, False)
    if not agreed:
        await call.answer("Поставь галочку согласия, иначе не смогу оформить подписку.", show_alert=True)
        return

    # лог согласия (без IP/UA)
    await save_consent(
        session,
        user_id=uid,
        plan=plan,
        price_rub=plan_amount(plan),
        period_days=plan_period_days(plan),
    )

    # создаём инвойс и генерим ссылку; флаг Recurring внутри robokassa.py учитывает settings.RK_RECURRING_ENABLED
    svc = PaymentService(session)
    payment, invoice_uuid = await svc.create_invoice(tg_user_id=uid, plan=plan)
    try:
        inv_id = int(invoice_uuid[:8], 16)
    except Exception:
        inv_id = abs(hash(invoice_uuid)) % (2**31)

    pay_url = build_payment_link(
        amount_rub=float(plan_amount(plan)),
        inv_id=inv_id,
        user_id=uid,
        description=f"Подписка {plan}",
        recurring=True,  # если фичефлаг выключен — Recurring не добавится в URL
    )

    # карточка + кнопки «Оплатить/Проверить/Назад»
    text = card_text_u18(plan) if plan.endswith("_u18") else (
        f"🎟 <b>Подписка {plan}</b>\nЦена: {plan_amount(plan)} ₽{POLICY_HTML}"
    )
    await call.message.answer(text, reply_markup=pay_kb(pay_url))
    await call.answer()

# ---------- U18 выбор тарифов ----------
@router.callback_query(F.data.startswith("u18:tariff:"))
async def u18_tariff_consent(call: CallbackQuery):
    plan_code = call.data.split(":", 2)[-1]  # m1_u18|m3_u18|m6_u18
    uid = call.from_user.id
    if uid not in VERIFIED_USERS:
        await call.answer("Нет верификации. Нажми «Мне нет 18 лет» и пройди проверку.", show_alert=True)
        return
    CONSENT_STATE.setdefault(uid, {})[plan_code] = False
    await call.message.answer(consent_text(plan_code), reply_markup=consent_kb(plan_code, False))
    await call.answer()
