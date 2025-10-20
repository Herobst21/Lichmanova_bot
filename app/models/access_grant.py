# app/models/access_grant.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AccessGrant(Base):
    __tablename__ = "access_grants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    tg_user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)

    invite_link: Mapped[str | None] = mapped_column(String(255))
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    used: Mapped[bool] = mapped_column(Boolean, default=False)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
