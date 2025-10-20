# app/web/routes.py
from __future__ import annotations

import sys
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.services.payment_service import PaymentService

# для диагностики пути модуля
from app.web import robokassa_routes as rk  # импорт модулем, не router

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


# Диагностика: покажет, откуда реально подхватили robokassa_routes
@router.get("/_where")
async def where():
    return {
        "robokassa_routes_file": getattr(rk, "__file__", None),
        "sys_path_head": sys.path[:5],
    }


# Простая страничка для ручного теста «фейковой оплаты»
@router.get("/payments/fake/pay", response_class=HTMLResponse)
async def fake_pay_page(invoice_id: str):
    return HTMLResponse(
        f"""
        <!doctype html>
        <html>
          <head><meta charset="utf-8"><title>Fake Pay</title></head>
          <body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width: 640px; margin: 40px auto;">
            <h2>Оплата счёта</h2>
            <p>invoice_id: <code>{invoice_id}</code></p>
            <form method="post" action="/payments/fake/confirm">
              <input type="hidden" name="invoice_id" value="{invoice_id}">
              <button type="submit" style="padding:10px 16px; cursor:pointer;">Оплатить (фейк)</button>
            </form>
          </body>
        </html>
        """
    )


# Подтверждение «фейковой оплаты» с формы выше
@router.post("/payments/fake/confirm", response_class=HTMLResponse)
async def fake_confirm(
    invoice_id: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    svc = PaymentService(session)
    await svc.confirm_payment(invoice_id)
    return HTMLResponse("<h3>Оплата прошла. Подписка активирована/продлена.</h3>")


# Унифицированный вебхук-приёмник (на будущее/отладку)
@router.post("/payments/webhook")
async def payments_webhook(
    req: Request,
    session: AsyncSession = Depends(get_session),
):
    # Пытаемся прочитать JSON, если не получилось — пустой dict
    try:
        data = await req.json()
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    provider = str(data.get("provider", "")).lower()
    invoice_id = data.get("invoice_id")
    status = str(data.get("status", "")).lower()

    if provider in {"fake", "robokassa"} and status == "paid" and invoice_id:
        svc = PaymentService(session)
        await svc.confirm_payment(str(invoice_id))
        return JSONResponse({"ok": True})

    return JSONResponse({"ok": True})

# ВАЖНО: НЕ монтируем здесь robokassa_routes.router.
# Его включает только server.py, чтобы не было дублей путей.
