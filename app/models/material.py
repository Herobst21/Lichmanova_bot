from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from .base import Base

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # URL или текст
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
