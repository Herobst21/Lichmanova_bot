from __future__ import annotations
from typing import List, Optional

from pydantic import Field, AliasChoices, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_csv_ints(value: str | List[int] | None) -> List[int]:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return [int(x) for x in value]
    if isinstance(value, int):
        return [value]
    parts = [p.strip() for p in str(value).split(",") if p.strip()]
    return [int(p) for p in parts]


class Settings(BaseSettings):
    # === Telegram ===
    BOT_TOKEN: str = ""
    OWNER_ID: Optional[int] = None
    ADMINS: List[int] = Field(default_factory=list)

    # === Storage / DB ===
    DATABASE_URL: Optional[str] = None
    POSTGRES_DSN: Optional[str] = None

    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    REDIS_DSN: Optional[str] = None  # web может не использовать redis

    # === Контент / приватные чаты ===
    CONTENT_CHANNEL_ID: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CONTENT_CHANNEL_ID", "PRIVATE_CHANNEL_ID"),
    )
    PRIVATE_CHAT_ID: Optional[int] = None

    INVITE_TTL_HOURS: int = 168
    GRACE_HOURS: int = 24

    # === Подписка / триал ===
    TRIAL_ENABLED: bool = True
    TRIAL_MODE: str = Field("paid", description="paid | free | off")
    TRIAL_DAYS: int = 3
    TRIAL_PRICE: int = 10
    AUTO_RENEW_DEFAULT: bool = True

    AUTO_RENEW_PLAN: Optional[str] = None
    TRIAL_CONVERT_PLAN: Optional[str] = None  # legacy alias

    # === Цены тарифов ===
    PLAN_PRICES_RUB: str = "m1:990,m3:2490,m12:8990"

    # === Платёжный провайдер ===
    PAYMENT_PROVIDER: str = Field("rk", description="fake | telegram | rk | robokassa")
    PAYMENT_PROVIDER_TOKEN: Optional[str] = None
    BASE_CURRENCY: str = "RUB"

    # === Robokassa ===
    RK_RECURRING_ENABLED: bool = False

    # === Веб-приложение / вебхуки ===
    PUBLIC_BASE_URL: str = "http://localhost:8080"
    WEBHOOK_URL: str = ""
    WEBAPP_HOST: str = "0.0.0.0"
    WEBAPP_PORT: int = 8080

    # === Планировщик / напоминания ===
    SCHEDULER_TZ: str = "UTC"
    REMINDERS_HOURS_BEFORE: List[int] = Field(default_factory=lambda: [72, 24, 3])

    # === Отладка SQL ===
    SQL_ECHO: bool = False

    # === Логи ===
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")
    log_sql: str = Field(default="WARNING", alias="LOG_SQL")
    log_aiogram: str = Field(default="INFO", alias="LOG_AIOGRAM")

    # === Поддержка/верификация возраста ===
    SUPPORT_URL: str = Field(default="https://t.me/your_support_here")
    AGE_VERIFY_ADMIN_ID: Optional[int] = Field(
        default=None,
        description="Куда слать паспорта на модерацию; если не задано — возьмем OWNER_ID или первого из ADMINS",
    )

    # Дополнительные ссылки (используются в хендлерах)
    OFFERTA_URL: str = "https://example.com/offer"
    PRIVACY_URL: str = "https://example.com/privacy"

    # === Robokassa (должны быть объявлены, иначе env игнорится) ===
    ROBOKASSA_LOGIN: str | None = None
    ROBOKASSA_PASSWORD1: str | None = None
    ROBOKASSA_PASSWORD2: str | None = None
    ROBOKASSA_TEST: int | None = 1
    ROBOKASSA_CULTURE: str | None = "ru"

    # ---- валидаторы ДО валидации типов ----
    @field_validator("ADMINS", mode="before")
    @classmethod
    def _v_admins(cls, v):
        return _parse_csv_ints(v)

    @field_validator("REMINDERS_HOURS_BEFORE", mode="before")
    @classmethod
    def _v_reminders(cls, v):
        if v is None or v == "":
            return [72, 24, 3]
        if isinstance(v, (list, tuple)):
            return [int(x) for x in v]
        if isinstance(v, str):
            return _parse_csv_ints(v)
        return v

    # ---- пост-обработчик ----
    def model_post_init(self, __context) -> None:
        # телеграм-провайдер требует токен
        if self.PAYMENT_PROVIDER and self.PAYMENT_PROVIDER.lower() == "telegram" and not self.PAYMENT_PROVIDER_TOKEN:
            raise ValueError("PAYMENT_PROVIDER=telegram, но PAYMENT_PROVIDER_TOKEN не задан.")

        # совместимость DSN/URL
        if not self.DATABASE_URL and self.POSTGRES_DSN:
            self.DATABASE_URL = self.POSTGRES_DSN

        # дефолт для модерации возраста
        if not self.AGE_VERIFY_ADMIN_ID:
            if self.OWNER_ID:
                self.AGE_VERIFY_ADMIN_ID = self.OWNER_ID
            elif self.ADMINS:
                self.AGE_VERIFY_ADMIN_ID = self.ADMINS[0]

        # безопасный дефолт канала, если нужен int
        if self.CONTENT_CHANNEL_ID is None:
            # если где-то ожидается int, ниже можно привести к 0
            self.CONTENT_CHANNEL_ID = 0

    @model_validator(mode="after")
    def _backfill_trial_convert(self):
        if not self.AUTO_RENEW_PLAN and self.TRIAL_CONVERT_PLAN:
            self.AUTO_RENEW_PLAN = self.TRIAL_CONVERT_PLAN
        if not self.TRIAL_CONVERT_PLAN and self.AUTO_RENEW_PLAN:
            self.TRIAL_CONVERT_PLAN = self.AUTO_RENEW_PLAN
        if not self.AUTO_RENEW_PLAN and not self.TRIAL_CONVERT_PLAN:
            self.AUTO_RENEW_PLAN = self.TRIAL_CONVERT_PLAN = "m1"
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
