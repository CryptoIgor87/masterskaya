import os
import time
from datetime import date
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from urllib.parse import quote
from web.app import templates
from config import UPLOADS_DIR, BASE_PATH
import database as db

router = APIRouter(prefix="/admin/promotions", tags=["promotions"])


def _save_photo(photo_content: bytes, ext: str) -> str:
    filename = f"promo_{int(time.time())}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(photo_content)
    return filename


@router.get("")
async def list_promotions(request: Request):
    promotions = await db.get_all_promotions()
    flash_msg = request.query_params.get("msg", "")
    flash_type = request.query_params.get("type", "info")
    return templates.TemplateResponse("promotions.html", {
        "request": request,
        "promotions": promotions,
        "active_page": "promotions",
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    })


@router.get("/add")
async def add_promotion_form(request: Request):
    return templates.TemplateResponse("promotion_form.html", {
        "request": request,
        "active_page": "promotions",
        "promo": None,
    })


@router.post("/add")
async def add_promotion(
    title: str = Form(...),
    description: str = Form(...),
    start_date: str = Form(""),
    end_date: str = Form(""),
    is_active: int = Form(0),
    is_perpetual: int = Form(0),
    photo: UploadFile = File(None),
):
    try:
        photo_path = None
        if photo and photo.filename:
            ext = os.path.splitext(photo.filename)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                content = await photo.read()
                photo_path = _save_photo(content, ext)

        sd = date.fromisoformat(start_date) if start_date else None
        ed = date.fromisoformat(end_date) if end_date else None
        await db.add_promotion(title, description, photo_path, sd, ed, is_active, is_perpetual)
        return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)
    except Exception as e:
        msg = quote(f"Ошибка при создании акции: {e}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/promotions?msg={msg}&type=danger",
            status_code=303,
        )


@router.get("/{promotion_id}/edit")
async def edit_promotion_form(request: Request, promotion_id: int):
    promo = await db.get_promotion(promotion_id)
    if not promo:
        return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)
    return templates.TemplateResponse("promotion_form.html", {
        "request": request,
        "active_page": "promotions",
        "promo": promo,
    })


@router.post("/{promotion_id}/edit")
async def edit_promotion(
    promotion_id: int,
    title: str = Form(...),
    description: str = Form(...),
    start_date: str = Form(""),
    end_date: str = Form(""),
    is_active: int = Form(0),
    is_perpetual: int = Form(0),
    photo: UploadFile = File(None),
):
    try:
        promo = await db.get_promotion(promotion_id)
        if not promo:
            return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)

        photo_path = promo["photo_path"]
        if photo and photo.filename:
            ext = os.path.splitext(photo.filename)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                # Remove old photo
                if photo_path:
                    old_path = os.path.join(UPLOADS_DIR, photo_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                content = await photo.read()
                photo_path = _save_photo(content, ext)

        sd = date.fromisoformat(start_date) if start_date else None
        ed = date.fromisoformat(end_date) if end_date else None
        await db.update_promotion(promotion_id, title, description, photo_path, sd, ed, is_active, is_perpetual)
        msg = quote("Акция обновлена!")
        return RedirectResponse(
            f"{BASE_PATH}/admin/promotions?msg={msg}&type=success",
            status_code=303,
        )
    except Exception as e:
        msg = quote(f"Ошибка при обновлении акции: {e}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/promotions?msg={msg}&type=danger",
            status_code=303,
        )


@router.post("/{promotion_id}/toggle")
async def toggle_promotion(promotion_id: int):
    await db.toggle_promotion(promotion_id)
    return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)


@router.post("/{promotion_id}/delete")
async def delete_promotion(promotion_id: int):
    promo = await db.get_promotion(promotion_id)
    if promo and promo["photo_path"]:
        filepath = os.path.join(UPLOADS_DIR, promo["photo_path"])
        if os.path.exists(filepath):
            os.remove(filepath)
    await db.delete_promotion(promotion_id)
    return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)
