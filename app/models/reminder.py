from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, func
from .base import Base

class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(16), index=True) # trial_end | sub_end
    due_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    sent_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
