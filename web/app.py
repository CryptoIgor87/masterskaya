from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, APIRouter, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os
from config import UPLOADS_DIR, BASE_PATH, SECRET_KEY, ADMIN_LOGIN, ADMIN_PASSWORD

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

    from web.routes import promotions, bonuses, clients, feedback, mailings

    parent = APIRouter(prefix=BASE_PATH)
    parent.include_router(promotions.router)
    parent.include_router(bonuses.router)
    parent.include_router(clients.router)
    parent.include_router(feedback.router)
    parent.include_router(mailings.router)
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

        return await call_next(request)

    # --- Session middleware (outer — added last) ---
    app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

    return app
