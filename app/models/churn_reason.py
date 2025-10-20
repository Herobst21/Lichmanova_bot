from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from .base import Base

class ChurnReason(Base):
    __tablename__ = "churn_reasons"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    reason_code: Mapped[str] = mapped_column(String(16))
    reason_text: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
