# app/models/user.py
from __future__ import annotations

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, nullable=False, index=True, unique=True)

    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    blocked = Column(Boolean, nullable=False, default=False)
    trial_used = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 🔽 добавили обратную связь к подпискам
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )
