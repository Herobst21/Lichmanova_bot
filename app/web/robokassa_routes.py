# app/web/robokassa_routes.py
from __future__ import annotations

import hashlib
import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.config import settings

router = APIRouter()
log = logging.getLogger("robokassa")       # боевые пути (result)
debug_router = APIRouter() 

# === helpers ===

def _sig_parts(login: str, out_sum: str, inv_id: str, p2: str, shp: Dict[str, str]):
    """
    Возвращает (sig_hex, base_string, shp_sorted).
    Формат базы: login:OutSum:InvId:Password2[:Shp_key=value ...] с Shp_* в алфавитном порядке.
    """
    shp_sorted = dict(sorted(shp.items())) if shp else {}
    base = f"{login}:{out_sum}:{inv_id}:{p2}"
    for k, v in shp_sorted.items():
        base += f":{k}={v}"
    sig = hashlib.sha256(base.encode()).hexdigest()
    return sig, base, shp_sorted


def _safe_headers(request: Request) -> Dict[str, str]:
    """Часть заголовков для логов, без мусора и приватного."""
    allow = {"content-type", "content-length", "user-agent", "x-request-id", "x-real-ip", "x-forwarded-for"}
    return {k.lower(): v for k, v in request.headers.items() if k.lower() in allow}


async def _read_payload(request: Request) -> Dict[str, Any]:
    """Пробуем json -> form -> query, чтобы не падать на типе контента."""
    data: Dict[str, Any] = {}
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            j = await request.json()
            if isinstance(j, dict):
                data = j
                return data
    except Exception as e:
        log.debug("payload_json_error: %s", repr(e))

    try:
        form = await request.form()
        data = dict(form.items())
        if data:
            return data
    except Exception as e:
        log.debug("payload_form_error: %s", repr(e))

    data = dict(request.query_params.items())
    return data


def _tail(s: str | None, n: int = 4) -> str:
    s = s or ""
    return s[-n:] if len(s) >= n else s


def _length(s: str | None) -> int:
    return len(s or "")


# === prod endpoint ===

@router.post("/robokassa/result")
async def rk_result(request: Request):
    """
    Result URL (Robokassa): верификация подписи.
    Возвращает "OK<InvId>" при успехе, иначе 400 + debug-текст.
    """
    rid = getattr(request.state, "request_id", "-")
    method, path = request.method, request.url.path
    hdr = _safe_headers(request)
    log.info("rk_result_in rid=%s method=%s path=%s headers=%s", rid, method, path, hdr)

    form = await _read_payload(request)
    log.info("rk_result_parsed rid=%s payload_keys=%s payload_preview=%s",
             rid, sorted(list(form.keys()))[:12], {k: form[k] for k in list(form)[:6]})

    out_sum = str(form.get("OutSum") or "")
    inv_id = str(form.get("InvId") or form.get("InvoiceID") or "")
    sig_in = str(form.get("SignatureValue") or "").lower()
    shp = {k: str(v) for k, v in form.items() if k.startswith("Shp_")}

    # БЕЗОПАСНО: не падаем, если атрибутов нет в Settings
    login = getattr(settings, "ROBOKASSA_LOGIN", "") or ""
    p2    = getattr(settings, "ROBOKASSA_PASSWORD2", "") or ""

    sig_calc, base_string, shp_sorted = _sig_parts(login, out_sum, inv_id, p2, shp)
    log.info("rk_result_calc rid=%s inv_id=%s out_sum=%s shp=%s base=%s sig_calc=%s sig_in=%s",
             rid, inv_id, out_sum, shp_sorted, base_string, sig_calc, sig_in)

    if sig_calc.lower() != sig_in:
        log.warning(
            "rk_result_bad_sign rid=%s login_tail=%s p2_len=%d p2_tail=%s out_sum=%s inv_id=%s shp=%s sig_in=%s sig_calc=%s",
            rid, _tail(login), _length(p2), _tail(p2, 2), out_sum, inv_id, shp_sorted, sig_in, sig_calc
        )
        debug_text = (
            "bad sign (debug)\n"
            f"login_tail={_tail(login)!r}\n"
            f"p2_len={_length(p2)} p2_tail={_tail(p2, 2)!r}\n"
            f"OutSum={out_sum!r}\n"
            f"InvId={inv_id!r}\n"
            f"Shp_sorted={shp_sorted!r}\n"
            f"sig_in={sig_in}\n"
            f"sig_calc={sig_calc}\n"
            "calc_base_format: 'login:OutSum:InvId:Password2[:Shp_key=value ...]' (Shp_* sorted)\n"
            f"calc_base_string={base_string!r}\n"
        )
        return Response(debug_text, status_code=400, media_type="text/plain; charset=utf-8")

    log.info("rk_result_ok rid=%s inv_id=%s", rid, inv_id)
    return Response(f"OK{inv_id}", media_type="text/plain")


# === diagnostics ===

@router.get("/robokassa/_where")
async def rk_where():
    """Путь файла, из которого реально импортирован этот роутер."""
    return {"__file__": __file__}


@router.get("/robokassa/_env")
async def rk_env(request: Request):
    """
    Диагностика окружения Robokassa: ничего секретного.
    Не падает даже при пустых .env значениях.
    """
    rid = getattr(request.state, "request_id", "-")
    try:
        login = getattr(settings, "ROBOKASSA_LOGIN", "") or ""
    except Exception:
        login = ""
    try:
        p1 = getattr(settings, "ROBOKASSA_PASSWORD1", "") or ""
    except Exception:
        p1 = ""
    try:
        p2 = getattr(settings, "ROBOKASSA_PASSWORD2", "") or ""
    except Exception:
        p2 = ""
    try:
        test = int(getattr(settings, "ROBOKASSA_TEST", 1) or 1)
    except Exception:
        test = 1
    try:
        pbu = getattr(settings, "PUBLIC_BASE_URL", "") or ""
    except Exception:
        pbu = ""

    payload = {
        "login_tail": _tail(login),
        "password1_tail": _tail(p1),
        "password2_tail": _tail(p2),
        "password1_len": _length(p1),
        "password2_len": _length(p2),
        "test": test,
        "public_base_url": pbu,
    }
    log.info(
        "rk_env_dump rid=%s login_tail=%s p1_len=%d p2_len=%d test=%s public_base_url=%s",
        rid, payload["login_tail"], payload["password1_len"], payload["password2_len"], test, pbu
    )
    # Всегда 200, это чисто диагностика
    return JSONResponse(payload)


@router.post("/robokassa/_calc")
async def rk_calc(request: Request):
    """
    Тестовый калькулятор подписи.
    Принимает JSON/form/query с полями:
      login, out_sum, inv_id (или InvoiceID), password2, и произвольные Shp_*
    """
    rid = getattr(request.state, "request_id", "-")
    hdr = _safe_headers(request)
    log.info("rk_calc_in rid=%s method=%s path=%s headers=%s", rid, request.method, request.url.path, hdr)

    data = await _read_payload(request)
    log.info("rk_calc_parsed rid=%s payload_keys=%s payload_preview=%s",
             rid, sorted(list(data.keys()))[:12], {k: data[k] for k in list(data)[:6]})

    out_sum = str(data.get("out_sum") or data.get("OutSum") or "")
    inv_id = str(data.get("inv_id") or data.get("InvId") or data.get("InvoiceID") or "")
    # БЕЗОПАСНО: берём из payload, затем из настроек, не падаем при отсутствии атрибутов
    login = str(data.get("login") or getattr(settings, "ROBOKASSA_LOGIN", "") or "")
    p2    = str(data.get("password2") or data.get("Password2") or getattr(settings, "ROBOKASSA_PASSWORD2", "") or "")

    shp = {k: str(v) for k, v in data.items() if k.startswith("Shp_")}
    sig_calc, base_string, shp_sorted = _sig_parts(login, out_sum, inv_id, p2, shp)

    log.info("rk_calc_done rid=%s base=%s sig_calc=%s login_tail=%s p2_len=%d p2_tail=%s",
             rid, base_string, sig_calc, _tail(login), _length(p2), _tail(p2, 2))

    return {
        "login_tail": _tail(login),
        "OutSum": out_sum,
        "InvId": inv_id,
        "Shp_sorted": shp_sorted,
        "p2_len": _length(p2),
        "p2_tail": _tail(p2, 2),
        "calc_base_string": base_string,
        "sig_calc": sig_calc,
    }


# === diagnostics ===

@debug_router.get("/robokassa/_where")
async def rk_where():
    return {"__file__": __file__}

@debug_router.get("/robokassa/_env")
async def rk_env(request: Request):
    ...
    return JSONResponse(payload)

@debug_router.post("/robokassa/_calc")
async def rk_calc(request: Request):
    ...
    return {...}
