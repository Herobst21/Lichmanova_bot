# roboweb/app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
import hashlib
import os
import logging

logging.basicConfig(level=logging.INFO)
api = FastAPI()

P2 = os.getenv("ROBOKASSA_PASSWORD2", "").strip()

def _calc_sign(out_sum: str, inv_id: str, shp: dict) -> str:
    """
    Robokassa (SHA256):
      SignatureValue = sha256(OutSum:InvId:Password2[:Shp_*...]).hexdigest().lower()
    Если используешь кастомные Shp_* параметры — включаем их в подпись в алфавитном порядке.
    """
    base = f"{out_sum}:{inv_id}:{P2}"
    if shp:
        base += ":" + ":".join(f"{k}={shp[k]}" for k in sorted(shp))
    return hashlib.sha256(base.encode("utf-8")).hexdigest().lower()

@api.get("/health")
def health():
    return JSONResponse({"ok": True})

@api.get("/robokassa/success")
def success():
    return JSONResponse({"status": "success", "msg": "Оплата прошла. Вернись в Telegram-бот."})

@api.get("/robokassa/fail")
def fail():
    return JSONResponse({"status": "fail", "msg": "Оплата не прошла."})

@api.post("/robokassa/result")
async def result(request: Request):
    form = await request.form()
    out_sum = str(form.get("OutSum", ""))
    inv_id = str(form.get("InvId", ""))
    incoming = str(form.get("SignatureValue", "")).lower()

    # Собираем Shp_* (если их использует твой флоу)
    shp = {k: str(v) for k, v in form.items() if k.startswith("Shp_")}

    # Валидация подписи
    expected = _calc_sign(out_sum, inv_id, shp)
    if incoming != expected:
        logging.warning("Bad signature: inv=%s out_sum=%s incoming=%s expected=%s",
                        inv_id, out_sum, incoming, expected)
        return PlainTextResponse("bad sign", status_code=400)

    # Никаких внешних вызовов здесь не нужно: бот сам активирует подписку при проверке оплаты.
    # Robokassa ждёт 'OK<InvId>' — возвращаем.
    return PlainTextResponse(f"OK{inv_id}", status_code=200)
