from urllib.parse import quote
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from web.app import templates
from config import BASE_PATH
import database as db

router = APIRouter(prefix="/admin/clients", tags=["clients"])


@router.get("")
async def list_clients(request: Request):
    clients = await db.get_all_clients()
    flash_msg = request.query_params.get("msg", "")
    flash_type = request.query_params.get("type", "info")
    return templates.TemplateResponse("clients.html", {
        "request": request,
        "clients": clients,
        "active_page": "clients",
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    })


@router.post("/{client_id}/update")
async def update_client(client_id: int, first_name: str = Form(""), phone: str = Form("")):
    await db.update_client_info(client_id, first_name.strip(), phone.strip())
    msg = quote("Данные клиента обновлены")
    return RedirectResponse(
        f"{BASE_PATH}/admin/clients?msg={msg}&type=success",
        status_code=303,
    )


@router.post("/{client_id}/delete")
async def delete_client(client_id: int):
    await db.delete_client(client_id)
    msg = quote("Клиент удалён")
    return RedirectResponse(
        f"{BASE_PATH}/admin/clients?msg={msg}&type=success",
        status_code=303,
    )


@router.post("/{client_id}/message")
async def send_message(request: Request, client_id: int, message_text: str = Form(...)):
    client = await db.get_client(client_id)
    if not client:
        msg = quote("Клиент не найден")
        return RedirectResponse(
            f"{BASE_PATH}/admin/clients?msg={msg}&type=danger",
            status_code=303,
        )
    bot = request.app.state.bot
    try:
        await bot.send_message(chat_id=client["telegram_id"], text=message_text)
        name = client["first_name"] or str(client["telegram_id"])
        msg = quote(f"Сообщение отправлено клиенту {name}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/clients?msg={msg}&type=success",
            status_code=303,
        )
    except Exception as e:
        msg = quote(f"Ошибка отправки: {e}")
        return RedirectResponse(
            f"{BASE_PATH}/admin/clients?msg={msg}&type=danger",
            status_code=303,
        )
