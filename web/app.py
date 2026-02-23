from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
import os
from config import UPLOADS_DIR, BASE_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TOMSK_TZ = timezone(timedelta(hours=7))


def tomsk_time(value):
    """Convert UTC datetime to Tomsk time (UTC+7) and format."""
    if not value:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        local = value.astimezone(TOMSK_TZ)
        return local.strftime("%d.%m.%Y %H:%M")
    return str(value)


templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["B"] = BASE_PATH
templates.env.filters["tomsk"] = tomsk_time


def create_app(bot=None) -> FastAPI:
    app = FastAPI(title="Masterksya Admin")
    app.state.bot = bot

    app.mount(f"{BASE_PATH}/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    app.mount(f"{BASE_PATH}/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

    from web.routes import promotions, bonuses, clients, feedback, mailings

    parent = APIRouter(prefix=BASE_PATH)
    parent.include_router(promotions.router)
    parent.include_router(bonuses.router)
    parent.include_router(clients.router)
    parent.include_router(feedback.router)
    parent.include_router(mailings.router)
    app.include_router(parent)

    async def root():
        return RedirectResponse(f"{BASE_PATH}/admin/promotions")

    if BASE_PATH:
        app.add_api_route(BASE_PATH, root, methods=["GET"])
        app.add_api_route(f"{BASE_PATH}/", root, methods=["GET"])
    else:
        app.add_api_route("/", root, methods=["GET"])

    return app
