from fastapi import APIRouter, Request
from web.app import templates
import database as db

router = APIRouter(prefix="/admin/clients", tags=["clients"])


@router.get("")
async def list_clients(request: Request):
    clients = await db.get_all_clients()
    return templates.TemplateResponse("clients.html", {
        "request": request,
        "clients": clients,
        "active_page": "clients",
    })
