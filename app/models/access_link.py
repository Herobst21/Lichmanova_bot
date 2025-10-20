from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, Boolean, DateTime, func
from .base import Base

class AccessLink(Base):
    __tablename__ = "access_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    invite_link: Mapped[str | None] = mapped_column(nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
