# app/services/payment_service.py
from __future__ import annotations

import inspect
import logging
from types import SimpleNamespace
from typing import Tuple, Any, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import PendingRollbackError

from app.config import settings

logger = logging.getLogger(__name__)

_PLAN_DAYS = {"trial3_10": 3, "m1": 30, "m3": 90, "m12": 365}


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

        try:
            from app.repositories.payment_repo import PaymentRepo  # type: ignore
            self.payments = PaymentRepo(session)
        except Exception:
            self.payments = None  # type: ignore[attr-defined]

        try:
            from app.repositories.subscription_repo import SubscriptionRepo  # type: ignore
            self.subs_repo = SubscriptionRepo(session)
        except Exception:
            self.subs_repo = None  # type: ignore[attr-defined]

        try:
            from app.repositories.user_repo import UsersRepo  # type: ignore
            self.users_repo = UsersRepo(session)
        except Exception:
            self.users_repo = None  # type: ignore[attr-defined]

    # -------- helpers --------

    def _price_for_plan(self, plan: str) -> int:
        if plan == "trial3_10":
            return settings.TRIAL_PRICE
        price_map: dict[str, int] = {}
        for pair in settings.PLAN_PRICES_RUB.split(","):
            pair = pair.strip()
            if not pair:
                continue
            try:
                k, v = pair.split(":")
                price_map[k.strip()] = int(v.strip())
            except ValueError:
                continue
        return price_map.get(plan, price_map.get("m1", 990))

    def _days_for_plan(self, plan: str) -> int:
        return _PLAN_DAYS.get(plan, _PLAN_DAYS["m1"])

    async def _ensure_user(self, tg_user_id: int) -> int:
        """
        Гарантируем наличие пользователя в БД и возвращаем его PK.
        Учитываем, что users.tg_id NOT NULL.
        """
        # 1) если есть UsersRepo — используем его методы
        if self.users_repo:
            for meth in ("get_or_create_by_tg_id", "ensure_by_tg_id", "get_or_create"):
                if hasattr(self.users_repo, meth):
                    try:
                        res = await getattr(self.users_repo, meth)(tg_user_id)  # type: ignore[misc]
                        uid = getattr(res, "id", None)
                        if uid is None and isinstance(res, tuple) and res:
                            uid = getattr(res[0], "id", None)
                        if uid is not None:
                            return int(uid)
                    except Exception:
                        logger.exception("ensure_user via %s failed", meth)

        # 2) прямой доступ к модели
        try:
            from app.models.user import User  # type: ignore

            existing = await self.session.get(User, tg_user_id)
            if existing is not None:
                return int(existing.id)

            u = User(id=int(tg_user_id), tg_id=int(tg_user_id))
            self.session.add(u)
            await self.session.commit()
            return int(u.id)

        except PendingRollbackError:
            await self.session.rollback()
            try:
                from app.models.user import User  # type: ignore
                existing = await self.session.get(User, tg_user_id)
                if existing is not None:
                    return int(existing.id)
                u = User(id=int(tg_user_id), tg_id=int(tg_user_id))
                self.session.add(u)
                await self.session.commit()
                return int(u.id)
            except Exception:
                logger.exception("ensure_user retry failed")
                return int(tg_user_id)

        except Exception:
            logger.warning("No users repo/model or insert failed, fallback to tg_user_id=%s", tg_user_id)
            return int(tg_user_id)

    async def _repo_create_payment(self, **raw_kwargs) -> Optional[Any]:
        if not self.payments:
            return None

        kwargs = dict(raw_kwargs)
        if "invoice_id" in kwargs and "provider_invoice_id" not in kwargs:
            kwargs["provider_invoice_id"] = kwargs.pop("invoice_id")

        sig = inspect.signature(self.payments.create)  # type: ignore[union-attr]
        allowed = {k: v for k, v in kwargs.items() if k in sig.parameters}

        for attempt in (1, 2):
            try:
                return await self.payments.create(**allowed)  # type: ignore[misc]
            except PendingRollbackError:
                logger.warning("PaymentRepo.create: pending rollback, retrying once")
                await self.session.rollback()
                continue
            except Exception as e:
                logger.exception("PaymentRepo.create unexpected error: %s", e)
                return None
        return None

    async def _repo_get_by_invoice(self, invoice_id: str) -> Optional[Any]:
        if not self.payments:
            return None

        if hasattr(self.payments, "get_by_provider_invoice"):
            try:
                return await self.payments.get_by_provider_invoice(
                    settings.PAYMENT_PROVIDER, invoice_id
                )
            except Exception:
                logger.exception("payments.get_by_provider_invoice failed")

        for meth in ("get_by_invoice_id", "get_by_invoice", "get_by_provider_invoice_id"):
            if hasattr(self.payments, meth):
                try:
                    return await getattr(self.payments, meth)(invoice_id)  # type: ignore[misc]
                except Exception:
                    logger.exception("payments.%s failed", meth)

        return None

    async def _repo_mark_paid(self, payment_obj: Any) -> None:
        if not self.payments:
            return
        pid = getattr(payment_obj, "id", None)
        if isinstance(payment_obj, dict) and pid is None:
            pid = payment_obj.get("id")

        for meth, args in (
            ("mark_paid", (pid,)),
            ("set_status", (pid, "paid")),
            ("update", (pid, {"status": "paid"})),
        ):
            if hasattr(self.payments, meth):
                try:
                    await getattr(self.payments, meth)(*args)  # type: ignore[misc]
                    return
                except Exception:
                    logger.exception("payments.%s failed", meth)
        logger.warning("Could not mark payment as paid (no suitable repo method)")

    # -------- public API --------

    async def create_invoice(
        self,
        tg_user_id: int,
        plan: str,
        provider_invoice_id: Optional[str] = None,
    ) -> Tuple[object, str]:
        """
        Создаёт платёж. Если передан provider_invoice_id, он будет сохранён в БД и
        возвращён как invoice_id, чтобы совпадать с тем, что уходит в провайдера.
        """
        invoice_id = provider_invoice_id or uuid4().hex
        amount = self._price_for_plan(plan)

        user_id = await self._ensure_user(tg_user_id)

        payment: Any = await self._repo_create_payment(
            user_id=user_id,
            plan=plan,
            amount=amount,
            currency=settings.BASE_CURRENCY,
            provider_invoice_id=invoice_id,
            provider=settings.PAYMENT_PROVIDER,
            status="pending",
        )

        if payment is None:
            payment = {
                "id": None,
                "user_id": user_id,
                "tg_user_id": tg_user_id,
                "plan": plan,
                "amount": amount,
                "currency": settings.BASE_CURRENCY,
                "provider": settings.PAYMENT_PROVIDER,
                "provider_invoice_id": invoice_id,
                "invoice_id": invoice_id,
                "status": "pending",
            }

        logger.info(
            "payment created: tg_id=%s plan=%s amount=%s invoice_id=%s",
            tg_user_id, plan, amount, invoice_id,
        )
        return payment, invoice_id

    async def confirm_payment(self, invoice_id: str) -> Any:
        payment = await self._repo_get_by_invoice(invoice_id)
        if payment is None:
            logger.warning("confirm_payment: invoice %s not found", invoice_id)
            raise RuntimeError("Платёж не найден")

        def g(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        tg_user_id = g(payment, "tg_user_id", g(payment, "user_id"))
        plan = g(payment, "plan") or "m1"
        if tg_user_id is None:
            raise RuntimeError("У платежа нет user_id")

        await self._repo_mark_paid(payment)

        user_id = await self._ensure_user(int(tg_user_id))

        if self.subs_repo is None:
            from datetime import timedelta
            from app.utils.dates import now_utc
            expires = now_utc() + timedelta(days=self._days_for_plan(plan))
            return SimpleNamespace(
                user_id=user_id,
                plan=plan,
                status="active",
                is_trial=(plan == "trial3_10"),
                expires_at=expires,
            )

        try:
            from datetime import timedelta
            from app.utils.dates import now_utc
            new_expires = now_utc() + timedelta(days=self._days_for_plan(plan))
            sub = await self.subs_repo.create_or_extend(
                user_id=user_id,
                plan=plan,
                new_expires_at=new_expires,
                is_trial=(plan == "trial3_10"),
                auto_renew=settings.AUTO_RENEW_DEFAULT,
            )
            logger.info(
                "confirm_payment: invoice=%s -> subscription updated user=%s plan=%s",
                invoice_id, user_id, plan,
            )
            return sub
        except Exception as e:
            logger.exception("confirm_payment: subscription update failed: %s", e)
            raise RuntimeError("Не удалось обновить подписку") from e

    async def user_has_active_subscription(self, tg_user_id: int) -> bool:
        """
        Проверяем активную подписку. Если репозитория нет — возвращаем False,
        а подтверждение делает /robokassa/result.
        """
        if self.subs_repo and hasattr(self.subs_repo, "has_active_by_tg"):
            try:
                return bool(await self.subs_repo.has_active_by_tg(tg_user_id))
            except Exception:
                logger.exception("subs_repo.has_active_by_tg failed")
        return False
