from urllib.parse import quote
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from web.app import templates
from config import BASE_PATH
import database as db

router = APIRouter(prefix="/admin/settings", tags=["settings"])


@router.get("")
async def settings_page(request: Request):
    welcome_text = await db.get_setting("welcome_text") or ""
    bonus_terms = await db.get_setting("bonus_terms") or ""
    default_enabled = await db.get_setting("default_bonus_enabled") == "1"
    default_amount = await db.get_setting("default_bonus_amount") or "0"
    clients = await db.get_all_clients()
    flash_msg = request.query_params.get("msg", "")
    flash_type = request.query_params.get("type", "info")
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active_page": "settings",
        "welcome_text": welcome_text,
        "bonus_terms": bonus_terms,
        "default_enabled": default_enabled,
        "default_amount": default_amount,
        "clients": clients,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    })


@router.post("/welcome-text")
async def update_welcome_text(welcome_text: str = Form("")):
    await db.set_setting("welcome_text", welcome_text.strip())
    msg = quote("Приветственный текст сохранён")
    return RedirectResponse(
        f"{BASE_PATH}/admin/settings?msg={msg}&type=success",
        status_code=303,
    )


@router.post("/bonus-terms")
async def update_bonus_terms(bonus_terms: str = Form("")):
    await db.set_setting("bonus_terms", bonus_terms.strip())
    msg = quote("Условия бонусной программы сохранены")
    return RedirectResponse(
        f"{BASE_PATH}/admin/settings?msg={msg}&type=success",
        status_code=303,
    )
