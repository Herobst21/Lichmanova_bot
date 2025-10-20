import os
import hashlib
import urllib.parse
from typing import Dict, Optional

from app.config import settings

RK_LOGIN    = os.getenv("ROBOKASSA_LOGIN", "")
RK_P1       = os.getenv("ROBOKASSA_PASSWORD1", "")
RK_TEST     = os.getenv("ROBOKASSA_TEST", "1")  # "1" демо, "0" боевой
RK_ENDPOINT = os.getenv(
    "ROBOKASSA_ENDPOINT",
    "https://auth.robokassa.ru/Merchant/Index.aspx",
)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _signature(out_sum: str, inv_id: int, shp: Dict[str, str]) -> str:
    """
    Формат: MerchantLogin:OutSum:InvId:Password1[:Shp_key=value ...] (Shp_* по алфавиту)
    """
    base = f"{RK_LOGIN}:{out_sum}:{inv_id}:{RK_P1}"
    if shp:
        for k in sorted(shp.keys()):
            base += f":{k}={shp[k]}"
    return sha256(base)

def build_payment_link(
    *,
    amount_rub: float,
    inv_id: int,
    user_id: int,
    description: str,
    shp_fields: Optional[Dict[str, str]] = None,
    recurring: bool = False,
) -> str:
    out_sum = f"{amount_rub:.2f}"

    # Shp_* для подписи и аналитики
    shp_fields = dict(shp_fields or {})
    shp_fields.setdefault("Shp_user", str(user_id))

    # базовые параметры
    qs: Dict[str, str] = {
        "MerchantLogin": RK_LOGIN,
        "OutSum": out_sum,
        "InvId": str(inv_id),
        "Description": description,
        "IsTest": RK_TEST,
        # пробрасываем Shp_user сразу, но подпись считаем по shp_fields
        "Shp_user": shp_fields["Shp_user"],
    }

    # URL-ы возвратов/нотификаций — явно в ссылку
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    qs.update({
        "SuccessURL": f"{base}/robokassa/success",
        "FailURL":    f"{base}/robokassa/fail",
        "ResultURL":  f"{base}/robokassa/result",
    })

    # подпись (с учетом всех Shp_*)
    sig = _signature(out_sum, inv_id, shp_fields)
    qs["SignatureValue"] = sig

    # прокидываем дополнительные Shp_* в query
    for k, v in shp_fields.items():
        qs[k] = v

    # рекуррентный «материнский» платёж — только если разрешено настройками
    if recurring and getattr(settings, "RK_RECURRING_ENABLED", False):
        qs["Recurring"] = "true"

    return f"{RK_ENDPOINT}?" + urllib.parse.urlencode(qs)
