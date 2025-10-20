from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey
from app.models.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="RUB")

    # 🔹 увеличено до 32 символов (ранее было 8)
    plan: Mapped[str] = mapped_column(String(32), nullable=False)

    # 🔹 увеличено до 64 символов (UUID/hashes)
    provider_invoice_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # 🔹 увеличено для надёжности (fake / robokassa / stripe)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)

    # 🔹 увеличено для гибкости: pending / paid / failed / refunded
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} user={self.user_id} plan={self.plan} "
            f"amount={self.amount} status={self.status}>"
        )
