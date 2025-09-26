# config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent        # /app
PROJECT_ROOT = BASE_DIR.parent                    # raíz del proyecto

def _bool(v, default=False):
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "t", "yes", "y", "on")

def _normalize_db_url(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url



class Config:
    # --- Flask / SQLAlchemy ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")  # cambia en producción

    # Si existe DATABASE_URL la usamos (Render). Si no, usamos una DB local.
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
    os.getenv("LOCAL_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "postgresql+psycopg://postgres@localhost:5432/patitas_db"
)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # (opcional, mejora la estabilidad de conexiones en Render)
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- QR público ---
    _RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    QR_PUBLIC_BASE_URL = os.getenv("QR_PUBLIC_BASE_URL", _RENDER_URL or "http://localhost:5000")
    ALLOWED_ORIGINS     = os.getenv("ALLOWED_ORIGINS", QR_PUBLIC_BASE_URL)

    # --- Subida de imágenes ---
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(PROJECT_ROOT / "uploads"))
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # --- Reseteo de contraseña ---
    TEMP_PWD_SECRET = os.getenv("TEMP_PWD_SECRET") 
    RESET_TOKEN_MAX_AGE = int(os.getenv("RESET_TOKEN_MAX_AGE", "3600")) 

    # --- Email SMTP---
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT   = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool(os.getenv("MAIL_USE_TLS", "1"), True)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")       
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    MAIL_TRANSPORT = os.getenv("MAIL_TRANSPORT", "smtp").lower()  # "smtp" | "sendgrid" | "mailgun"


def get_config():
    return Config()


