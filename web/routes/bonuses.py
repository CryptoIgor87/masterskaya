import string
import random
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from web.app import templates
from config import BASE_PATH
import database as db

router = APIRouter(prefix="/admin/bonuses", tags=["bonuses"])


def generate_promo_code() -> str:
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=6))
    return f"BONUS-{code}"


@router.get("")
async def list_bonuses(request: Request):
    bonuses = await db.get_all_bonuses_with_clients()
    clients = await db.get_all_clients()
    stats = await db.get_bonus_stats()
    default_enabled = await db.get_setting("default_bonus_enabled") == "1"
    default_amount = await db.get_setting("default_bonus_amount") or "0"
    flash_msg = request.query_params.get("msg", "")
    flash_type = request.query_params.get("type", "info")
    return templates.TemplateResponse("bonuses.html", {
        "request": request,
        "bonuses": bonuses,
        "clients": clients,
        "stats": stats,
        "active_page": "bonuses",
        "default_enabled": default_enabled,
        "default_amount": default_amount,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    })


@router.post("/assign-all")
async def assign_all(
    amount: int = Form(...),
    promo_code: str = Form(""),
):
    if not promo_code.strip():
        promo_code = generate_promo_code()
    await db.add_bonus_to_all(amount, promo_code)
    return RedirectResponse(f"{BASE_PATH}/admin/bonuses", status_code=303)


@router.post("/assign/{client_id}")
async def assign_to_client(
    client_id: int,
    amount: int = Form(...),
    promo_code: str = Form(""),
):
    if not promo_code.strip():
        promo_code = generate_promo_code()
    await db.add_bonus(client_id, amount, promo_code)
    return RedirectResponse(f"{BASE_PATH}/admin/bonuses", status_code=303)


@router.post("/{bonus_id}/delete")
async def delete_bonus(bonus_id: int):
    await db.delete_bonus(bonus_id)
    return RedirectResponse(f"{BASE_PATH}/admin/bonuses", status_code=303)


@router.post("/{bonus_id}/update-code")
async def update_code(
    bonus_id: int,
    promo_code: str = Form(...),
):
    await db.update_bonus_code(bonus_id, promo_code)
    return RedirectResponse(f"{BASE_PATH}/admin/bonuses", status_code=303)


@router.post("/redeem")
async def redeem_bonus(
    request: Request,
    promo_code: str = Form(...),
    amount: int = Form(...),
):
    result = await db.redeem_bonus_by_code(promo_code.strip(), amount)
    # Store flash message in query param for simplicity
    if result["found"]:
        return RedirectResponse(
            f"{BASE_PATH}/admin/bonuses?msg={result['message']}&type=success",
            status_code=303,
        )
    return RedirectResponse(
        f"{BASE_PATH}/admin/bonuses?msg={result['message']}&type=danger",
        status_code=303,
    )


@router.post("/default-settings")
async def update_default_settings(
    default_amount: int = Form(...),
    default_enabled: int = Form(0),
):
    await db.set_setting("default_bonus_amount", str(default_amount))
    await db.set_setting("default_bonus_enabled", str(default_enabled))
    return RedirectResponse(f"{BASE_PATH}/admin/bonuses", status_code=303)
