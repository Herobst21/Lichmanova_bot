# app/scripts/confirm_payment.py
"""
Ручная симуляция Robokassa result webhook.
Запуск внутри контейнера:
    docker compose exec -T app-web python app/scripts/confirm_payment.py
"""

import os
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict

# === ДАННЫЕ ИЗ БД (payments) ===
INV_ID  = "f4e85e044b9e4f83accc3a7d3e3daffc"  # payments.provider_invoice_id
OUT_SUM = "990.00"                            # payments.amount с двумя знаками

# === Shp_* РОВНО КАК В ССЫЛКЕ ===
SHP_FIELDS: Dict[str, str] = {
    "Shp_user": "943701972",
    "Shp_plan": "m1",
}

# Внутри контейнера бьём по IPv4, чтобы не упасть на ::1
BASE_URL = "http://127.0.0.1:8080"

def make_sig(login: str, out_sum: str, inv_id: str, p2: str, shp: Dict[str, str]) -> str:
    """
    MerchantLogin:OutSum:InvId:Password2[:Shp_key=value ...] (Shp_* по алфавиту)
    """
    base = f"{login}:{out_sum}:{inv_id}:{p2}"
    if shp:
        for k in sorted(shp.keys()):
            base += f":{k}={shp[k]}"
    return hashlib.sha256(base.encode()).hexdigest()

def main():
    login = os.getenv("ROBOKASSA_LOGIN")
    p2    = os.getenv("ROBOKASSA_PASSWORD2")

    print("[env] ROBOKASSA_LOGIN =", login)
    print("[env] ROBOKASSA_PASSWORD2 set:", bool(p2))

    if not login or not p2:
        print("ERROR: env пустые. Проверь .env.app-web для web-контейнера.")
        return

    sig = make_sig(login, OUT_SUM, INV_ID, p2, SHP_FIELDS)
    payload = {
        "OutSum": OUT_SUM,
        "InvId": INV_ID,
        "SignatureValue": sig,
        **SHP_FIELDS,
    }

    print("[calc] fields:", {
        "MerchantLogin": login,
        "OutSum": OUT_SUM,
        "InvId": INV_ID,
        "Password2": "***",
        "Shp_*": dict(sorted(SHP_FIELDS.items())),
    })
    print("[calc] SignatureValue:", sig)

    body = urllib.parse.urlencode(payload).encode()
    url = f"{BASE_URL}/robokassa/result"

    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("[resp]", resp.status, resp.read().decode())
    except urllib.error.HTTPError as e:
        print("[resp-HTTPError]", e.code, e.read().decode())
    except Exception as e:
        print("[resp-ERR]", repr(e))

if __name__ == "__main__":
    main()
