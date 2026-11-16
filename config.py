"""
PolicySetu — Backend Configuration
==================================
Modular configuration for Development, Testing, and Production environments.
Loads environment variables from .env using python-dotenv.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
try:
    DATA_DIR.mkdir(exist_ok=True)
except OSError:
    pass

# Automatically load environment variables from .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base Configuration with hardened security defaults."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "policysetu-dev-secret-key-civic-tech-2026")
    APP_NAME = "PolicySetu"
    APP_TAGLINE = "Bridging Government Policies & People."
    APP_VERSION = "1.0.0-beta"

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    JSON_AS_ASCII = False

    # Security & Session Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1")
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    MAX_CONTENT_LENGTH = 30 * 1024 * 1024  # 30 MB max request payload

    # Language support
    SUPPORTED_LANGUAGES = ["en", "hi", "mr"]
    DEFAULT_LANGUAGE = "en"
    TIMEZONE = "Asia/Kolkata"

    # Pagination Defaults
    DEFAULT_PER_PAGE = 10
    MAX_PER_PAGE = 50

    # LLM & AI Intelligence Engine (Strictly configured via Environment Variables)
    LLM_API_KEY = (
        os.environ.get("GEMINI_API_KEY") or
        os.environ.get("OPENAI_API_KEY") or
        os.environ.get("LLM_API_KEY") or
        None
    )
    LLM_PROVIDER = os.environ.get(
        "LLM_PROVIDER",
        "gemini" if os.environ.get("GEMINI_API_KEY") else ("openai" if os.environ.get("OPENAI_API_KEY") else "auto")
    )
    LLM_MODEL = os.environ.get(
        "LLM_MODEL",
        "gemini-1.5-flash" if os.environ.get("GEMINI_API_KEY") else "gpt-4o-mini"
    )
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL")


def _resolve_sqlite_uri(env_var_name, default_path):
    raw = os.environ.get(env_var_name)
    if raw:
        # Normalize cloud postgres URLs (Heroku / Supabase / Neon compatibility)
        if raw.startswith("postgres://"):
            return raw.replace("postgres://", "postgresql://", 1)
        if raw.startswith("postgresql://"):
            return raw
        if raw.startswith("sqlite:///") and not raw.startswith("sqlite:////"):
            path_part = raw.replace("sqlite:///", "")
            p = Path(path_part)
            if not p.is_absolute():
                p = (BASE_DIR / p).resolve()
            return f"sqlite:///{p.as_posix()}"
        return raw
    return f"sqlite:///{default_path.resolve().as_posix()}"


class DevelopmentConfig(Config):
    """Development Configuration with local SQLite database."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _resolve_sqlite_uri(
        "DATABASE_URL",
        DATA_DIR / "policysetu.db"
    )


class TestingConfig(Config):
    """Testing Configuration with in-memory or test SQLite database."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _resolve_sqlite_uri(
        "TEST_DATABASE_URL",
        DATA_DIR / "policysetu_test.db"
    )


class ProductionConfig(Config):
    """Hardened Production Configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"
    SQLALCHEMY_DATABASE_URI = _resolve_sqlite_uri(
        "DATABASE_URL",
        DATA_DIR / "policysetu.db"
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
