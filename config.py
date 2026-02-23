import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8608741974:AAEJpMGs5nn6FgM0W-_MOacDqag4VBxhErk")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "165288321"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.environ.get("UPLOADS_DIR", os.path.join(BASE_DIR, "uploads"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.vttlbeewxbwkikmxdlev:uhnkjL2XdAjOU1iD@aws-0-us-west-2.pooler.supabase.com:5432/postgres",
)
DB_SCHEMA = os.environ.get("DB_SCHEMA", "masterskaya")

WEB_HOST = os.environ.get("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("WEB_PORT", "8080"))
BASE_PATH = os.environ.get("BASE_PATH", "")  # e.g. "/masterskaya" for production

WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://example.com")

DEFAULT_BONUS_AMOUNT = int(os.environ.get("DEFAULT_BONUS_AMOUNT", "100"))
DEFAULT_BONUS_PROMO = os.environ.get("DEFAULT_BONUS_PROMO", "WELCOME")

ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "masteradmin2026")
SECRET_KEY = os.environ.get("SECRET_KEY", "mksya-s3cret-k3y-2026-xQ9p")
