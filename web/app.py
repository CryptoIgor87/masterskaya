import logging
import re
import traceback
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, APIRouter, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os
from config import (UPLOADS_DIR, BASE_PATH, SECRET_KEY,
                    ADMIN_LOGIN, ADMIN_PASSWORD,
                    MANAGER_LOGIN, MANAGER_PASSWORD)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TOMSK_TZ = timezone(timedelta(hours=7))

# Paths blocked for manager role (regex patterns, applied after BASE_PATH prefix is stripped)
MANAGER_BLOCKED = [
    r"^/admin/settings",
    r"^/admin/giveaways",
    r"^/admin/mailings",
    r"^/admin/promotions/add",
    r"^/admin/promotions/\d+/edit",
    r"^/admin/promotions/\d+/toggle",
    r"^/admin/promotions/\d+/delete",
    r"^/admin/bonuses/assign",
    r"^/admin/bonuses/\d+/delete",
    r"^/admin/bonuses/\d+/update-code",
    r"^/admin/bonuses/default-settings",
    r"^/admin/clients/\d+/delete",
]


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
    app = FastAPI(title="Masterskaya Admin")
    app.state.bot = bot

    app.mount(f"{BASE_PATH}/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    app.mount(f"{BASE_PATH}/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

    # --- Login / Logout routes (unprotected) ---

    @app.get(f"{BASE_PATH}/login")
    async def login_page(request: Request):
        if request.session.get("authenticated"):
            return RedirectResponse(f"{BASE_PATH}/admin/promotions")
        return templates.TemplateResponse("login.html", {"request": request})

    @app.post(f"{BASE_PATH}/login")
    async def login_submit(request: Request):
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")
        if username == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            request.session["authenticated"] = True
            request.session["role"] = "admin"
            return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)
        if username == MANAGER_LOGIN and password == MANAGER_PASSWORD:
            request.session["authenticated"] = True
            request.session["role"] = "manager"
            return RedirectResponse(f"{BASE_PATH}/admin/promotions", status_code=303)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверный логин или пароль",
        })

    @app.get(f"{BASE_PATH}/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(f"{BASE_PATH}/login")

    # --- Admin routes ---

    from web.routes import promotions, bonuses, clients, feedback, mailings, settings, giveaways

    parent = APIRouter(prefix=BASE_PATH)
    parent.include_router(promotions.router)
    parent.include_router(bonuses.router)
    parent.include_router(clients.router)
    parent.include_router(feedback.router)
    parent.include_router(mailings.router)
    parent.include_router(settings.router)
    parent.include_router(giveaways.router)
    app.include_router(parent)

    # --- Root redirect ---

    async def root():
        return RedirectResponse(f"{BASE_PATH}/admin/promotions")

    if BASE_PATH:
        app.add_api_route(BASE_PATH, root, methods=["GET"])
        app.add_api_route(f"{BASE_PATH}/", root, methods=["GET"])
    else:
        app.add_api_route("/", root, methods=["GET"])

    # --- Auth middleware (inner — added first) ---

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        login_url = f"{BASE_PATH}/login"

        # Allow unauthenticated access to login, static, uploads
        if (path == login_url or
                "/static/" in path or
                "/uploads/" in path):
            return await call_next(request)

        # Check if this path belongs to our app
        needs_auth = path.startswith(BASE_PATH) if BASE_PATH else True

        if needs_auth and not request.session.get("authenticated"):
            return RedirectResponse(login_url)

        # Store role in request state for templates
        role = request.session.get("role", "admin")
        request.state.role = role

        # Block restricted paths for manager
        if role == "manager" and needs_auth:
            # Strip BASE_PATH prefix to match patterns
            rel_path = path[len(BASE_PATH):] if BASE_PATH else path
            for pattern in MANAGER_BLOCKED:
                if re.match(pattern, rel_path):
                    return RedirectResponse(
                        f"{BASE_PATH}/admin/promotions", status_code=303,
                    )

        return await call_next(request)

    # --- Error-catching middleware ---

    @app.middleware("http")
    async def error_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            tb_str = "".join(tb)
            logger.error(f"ERROR on {request.method} {request.url}:\n{tb_str}")
            return PlainTextResponse(
                f"Error: {exc}\n\n{tb_str}", status_code=500,
            )

    # --- Session middleware (outer — added last) ---
    app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

    return app
