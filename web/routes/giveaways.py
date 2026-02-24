from datetime import datetime
from urllib.parse import quote
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from web.app import templates
from config import BASE_PATH
import database as db

router = APIRouter(prefix="/admin/giveaways", tags=["giveaways"])


@router.get("")
async def list_giveaways(request: Request):
    giveaways = await db.get_all_giveaways()
    bot_username = getattr(request.app.state, "bot_username", "bot")
    flash_msg = request.query_params.get("msg", "")
    flash_type = request.query_params.get("type", "info")
    return templates.TemplateResponse("giveaways.html", {
        "request": request,
        "giveaways": giveaways,
        "bot_username": bot_username,
        "active_page": "giveaways",
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    })


@router.post("/create")
async def create_giveaway(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    winner_count: int = Form(1),
    end_date: str = Form(...),
):
    try:
        dt = datetime.fromisoformat(end_date)
        await db.create_giveaway(title, description, winner_count, dt)
        msg = quote("Розыгрыш создан!")
        return RedirectResponse(
            f"{BASE_PATH}/admin/giveaways?msg={msg}&type=success",
            status_code=303,
        )
    except Exception as e:
        msg = quote(f"Ошибка при создании розыгрыша: {e}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/giveaways?msg={msg}&type=danger",
            status_code=303,
        )


@router.get("/{giveaway_id}")
async def giveaway_detail(request: Request, giveaway_id: int):
    gw = await db.get_giveaway(giveaway_id)
    if not gw:
        return RedirectResponse(f"{BASE_PATH}/admin/giveaways", status_code=303)
    participants = await db.get_giveaway_participants(giveaway_id)
    winners = await db.get_giveaway_winners(giveaway_id)
    bot_username = getattr(request.app.state, "bot_username", "bot")
    flash_msg = request.query_params.get("msg", "")
    flash_type = request.query_params.get("type", "info")
    return templates.TemplateResponse("giveaway_detail.html", {
        "request": request,
        "gw": gw,
        "participants": participants,
        "winners": winners,
        "bot_username": bot_username,
        "active_page": "giveaways",
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    })


@router.post("/{giveaway_id}/finish")
async def finish_giveaway(giveaway_id: int):
    try:
        winners = await db.finish_giveaway(giveaway_id)
        count = len(winners)
        msg = quote(f"Розыгрыш завершён! Победителей: {count}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/giveaways/{giveaway_id}?msg={msg}&type=success",
            status_code=303,
        )
    except Exception as e:
        msg = quote(f"Ошибка при завершении розыгрыша: {e}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/giveaways/{giveaway_id}?msg={msg}&type=danger",
            status_code=303,
        )


@router.post("/{giveaway_id}/delete")
async def delete_giveaway(giveaway_id: int):
    try:
        await db.delete_giveaway(giveaway_id)
        msg = quote("Розыгрыш удалён")
        return RedirectResponse(
            f"{BASE_PATH}/admin/giveaways?msg={msg}&type=success",
            status_code=303,
        )
    except Exception as e:
        msg = quote(f"Ошибка при удалении розыгрыша: {e}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/giveaways?msg={msg}&type=danger",
            status_code=303,
        )
