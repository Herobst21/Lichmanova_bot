from __future__ import annotations

from typing import Optional
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.payment import Payment
from app.config import settings


class PaymentRepo:
    def __init__(self, s: AsyncSession) -> None:
        self.s = s

    async def create(
        self,
        user_id: int,
        amount: int | float | Decimal,
        currency: str,
        plan: str,
        provider: str,
        provider_invoice_id: str,
        status: str = "pending",
    ) -> Payment:
        p = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            plan=plan,
            provider=provider,
            provider_invoice_id=provider_invoice_id,
            status=status,
        )
        self.s.add(p)
        await self.s.commit()
        await self.s.refresh(p)
        return p

    async def get_by_provider_invoice(
        self,
        provider: str,
        provider_invoice_id: str,
    ) -> Optional[Payment]:
        res = await self.s.execute(
            select(Payment).where(
                Payment.provider == provider,
                Payment.provider_invoice_id == provider_invoice_id,
            )
        )
        return res.scalar_one_or_none()

    # Алиасы под разные ожидания сервисов
    async def get_by_invoice_id(self, invoice_id: str) -> Optional[Payment]:
        return await self.get_by_provider_invoice(settings.PAYMENT_PROVIDER, invoice_id)

    async def get_by_invoice(self, invoice_id: str) -> Optional[Payment]:
        return await self.get_by_invoice_id(invoice_id)

    async def get_by_provider_invoice_id(self, invoice_id: str) -> Optional[Payment]:
        return await self.get_by_invoice_id(invoice_id)

    async def set_paid(self, payment_id: int) -> None:
        await self.s.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status="paid")
        )
        await self.s.commit()

    # Алиасы под _repo_mark_paid в PaymentService
    async def mark_paid(self, payment_id: int) -> None:
        await self.set_paid(payment_id)

    async def set_status(self, payment_id: int, status: str) -> None:
        await self.s.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status=status)
        )
        await self.s.commit()

    async def update(self, payment_id: int, values: dict) -> None:
        await self.s.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(**values)
        )
        await self.s.commit()
