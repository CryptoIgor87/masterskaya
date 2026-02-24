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


@router.get("")
async def list_promotions(request: Request):
    promotions = await db.get_all_promotions()
    return templates.TemplateResponse("promotions.html", {
        "request": request,
        "promotions": promotions,
        "active_page": "promotions",
    })


@router.get("/add")
async def add_promotion_form(request: Request):
    return templates.TemplateResponse("promotion_form.html", {
        "request": request,
        "active_page": "promotions",
    })


@router.post("/add")
async def add_promotion(
    title: str = Form(...),
    description: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    is_active: int = Form(0),
    photo: UploadFile = File(None),
):
    try:
        photo_path = None
        if photo and photo.filename:
            ext = os.path.splitext(photo.filename)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                filename = f"promo_{int(time.time())}{ext}"
                filepath = os.path.join(UPLOADS_DIR, filename)
                content = await photo.read()
                with open(filepath, "wb") as f:
                    f.write(content)
                photo_path = filename

        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
        await db.add_promotion(title, description, photo_path, sd, ed, is_active)
        return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)
    except Exception as e:
        msg = quote(f"Ошибка при создании акции: {e}")
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
