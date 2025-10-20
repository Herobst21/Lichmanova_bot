# app/providers/fake_payment_provider.py
from dataclasses import dataclass
from app.services.payment_service import PaymentService

@dataclass
class FakePaymentProvider:
    svc: PaymentService

    async def create_invoice(self, user_id: int, plan: str):
        """
        Создаёт запись в payments и возвращает (payment, provider_invoice_id, pay_link).
        """
        payment, invoice_id = await self.svc.create_invoice(user_id, plan)
        # Фейковая «ссылка на оплату». Можно заменить на реальный провайдер позже.
        pay_link = f"https://t.me/{'pay'}?start={invoice_id}"
        return payment, invoice_id, pay_link

    async def confirm_payment(self, provider_invoice_id: str):
        """
        Помечает платеж как оплаченный и активирует/продлевает подписку.
        """
        sub = await self.svc.mark_paid_and_activate(provider_invoice_id)
        return sub
