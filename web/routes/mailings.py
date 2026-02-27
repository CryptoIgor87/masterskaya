import os
import time
import asyncio
from typing import List
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from config import UPLOADS_DIR, BASE_PATH
from aiogram.types import FSInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from web.app import templates
import database as db

router = APIRouter(prefix="/admin/mailings", tags=["mailings"])


@router.get("")
async def list_mailings(request: Request):
    mailings = await db.get_all_mailings()
    return templates.TemplateResponse("mailings.html", {
        "request": request,
        "mailings": mailings,
        "active_page": "mailings",
    })


@router.get("/create")
async def create_form(request: Request):
    clients = await db.get_all_clients()
    return templates.TemplateResponse("mailing_form.html", {
        "request": request,
        "active_page": "mailings",
        "mailing": None,
        "clients": clients,
        "selected_ids": [],
    })


@router.post("/create")
async def create_mailing(
    text: str = Form(...),
    button_text: str = Form(""),
    button_url: str = Form(""),
    target: str = Form("all"),
    client_ids: List[str] = Form([]),
    photo: UploadFile = File(None),
):
    photo_path = None
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            filename = f"mail_{int(time.time())}{ext}"
            filepath = os.path.join(UPLOADS_DIR, filename)
            content = await photo.read()
            with open(filepath, "wb") as f:
                f.write(content)
            photo_path = filename

    ids_str = ",".join(client_ids) if target == "selected" else ""
    await db.create_mailing(
        text=text,
        photo_path=photo_path,
        button_text=button_text.strip() or None,
        button_url=button_url.strip() or None,
        target=target,
        client_ids=ids_str,
    )
    return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)


@router.get("/{mailing_id}/edit")
async def edit_form(mailing_id: int, request: Request):
    mailing = await db.get_mailing(mailing_id)
    if not mailing or mailing["status"] != "draft":
        return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)
    clients = await db.get_all_clients()
    cids = mailing.get("client_ids") or ""
    selected_ids = [s.strip() for s in cids.split(",") if s.strip()]
    return templates.TemplateResponse("mailing_form.html", {
        "request": request,
        "active_page": "mailings",
        "mailing": mailing,
        "clients": clients,
        "selected_ids": selected_ids,
    })


@router.post("/{mailing_id}/edit")
async def edit_mailing(
    mailing_id: int,
    text: str = Form(...),
    button_text: str = Form(""),
    button_url: str = Form(""),
    target: str = Form("all"),
    client_ids: List[str] = Form([]),
    photo: UploadFile = File(None),
):
    mailing = await db.get_mailing(mailing_id)
    if not mailing or mailing["status"] != "draft":
        return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)

    photo_path = mailing["photo_path"]
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            # Remove old photo
            if photo_path:
                old = os.path.join(UPLOADS_DIR, photo_path)
                if os.path.exists(old):
                    os.remove(old)
            filename = f"mail_{int(time.time())}{ext}"
            filepath = os.path.join(UPLOADS_DIR, filename)
            content = await photo.read()
            with open(filepath, "wb") as f:
                f.write(content)
            photo_path = filename

    ids_str = ",".join(client_ids) if target == "selected" else ""
    await db.update_mailing(
        mailing_id,
        text=text,
        photo_path=photo_path,
        button_text=button_text.strip() or None,
        button_url=button_url.strip() or None,
        target=target,
        client_ids=ids_str,
    )
    return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)


@router.post("/{mailing_id}/send")
async def send_mailing(mailing_id: int, request: Request):
    mailing = await db.get_mailing(mailing_id)
    if not mailing or mailing["status"] != "draft":
        return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)

    bot = request.app.state.bot
    if not bot:
        return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)

    target = mailing.get("target") or "all"
    if target == "no_redemptions":
        telegram_ids = await db.get_client_telegram_ids_no_redemptions()
    elif target == "selected":
        cids_str = mailing.get("client_ids") or ""
        cids = [int(x) for x in cids_str.split(",") if x.strip()]
        telegram_ids = await db.get_client_telegram_ids_by_ids(cids) if cids else []
    else:
        telegram_ids = await db.get_all_client_telegram_ids()
    sent_total = len(telegram_ids)
    sent_ok = 0
    sent_fail = 0

    # Build keyboard if button exists
    reply_markup = None
    if mailing["button_text"] and mailing["button_url"]:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=mailing["button_text"],
            url=mailing["button_url"]
        ))
        reply_markup = builder.as_markup()

    # Build photo
    photo_file = None
    if mailing["photo_path"]:
        path = os.path.join(UPLOADS_DIR, mailing["photo_path"])
        if os.path.exists(path):
            photo_file = FSInputFile(path)

    for tid in telegram_ids:
        try:
            if photo_file:
                await bot.send_photo(
                    chat_id=tid,
                    photo=photo_file,
                    caption=mailing["text"],
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            else:
                await bot.send_message(
                    chat_id=tid,
                    text=mailing["text"],
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            sent_ok += 1
        except Exception:
            sent_fail += 1
        await asyncio.sleep(0.05)  # Rate limit protection

    await db.update_mailing_stats(mailing_id, sent_total, sent_ok, sent_fail)
    return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)


@router.post("/{mailing_id}/delete")
async def delete_mailing(mailing_id: int):
    mailing = await db.get_mailing(mailing_id)
    if mailing and mailing["photo_path"]:
        filepath = os.path.join(UPLOADS_DIR, mailing["photo_path"])
        if os.path.exists(filepath):
            os.remove(filepath)
    await db.delete_mailing(mailing_id)
    return RedirectResponse(f"{BASE_PATH}/admin/mailings", status_code=303)
