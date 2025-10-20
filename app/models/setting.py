from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from .base import Base

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(2048))
