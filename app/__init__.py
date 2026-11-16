"""
PolicySetu — Flask Application Factory
Bridging Government Policies & People.
"""

import os
from flask import Flask, g, request, session, render_template
from config import config as app_configs
from app.extensions import db, migrate


def create_app(config_name=None):
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # ── Configuration ────────────────────────────────────────────────────────
    config_obj = app_configs.get(config_name or os.environ.get("FLASK_ENV", "default"), app_configs["default"])
    app.config.from_object(config_obj)

    # ── Initialize Extensions ────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)

    app.config["FUTURE_LANGUAGES"] = [
        {"code": "bn", "native_name": "বাংলা", "english_name": "Bengali"},
        {"code": "gu", "native_name": "ગુજરાતી", "english_name": "Gujarati"},
        {"code": "ta", "native_name": "தமிழ்", "english_name": "Tamil"},
        {"code": "te", "native_name": "తెలుగు", "english_name": "Telugu"},
        {"code": "kn", "native_name": "ಕನ್ನಡ", "english_name": "Kannada"},
        {"code": "ml", "native_name": "മലയാളം", "english_name": "Malayalam"},
        {"code": "pa", "native_name": "ਪੰਜਾਬੀ", "english_name": "Punjabi"},
        {"code": "or", "native_name": "ଓଡ଼ିଆ", "english_name": "Odia"},
    ]

    # ── Load Translation Dictionaries (Expandable Architecture) ───────────────
    import json
    translations = {}
    i18n_dir = os.path.join(os.path.dirname(__file__), "i18n")
    if os.path.exists(i18n_dir):
        for fname in os.listdir(i18n_dir):
            if fname.endswith(".json"):
                code = fname[:-5]
                try:
                    with open(os.path.join(i18n_dir, fname), "r", encoding="utf-8") as f:
                        translations[code] = json.load(f)
                except Exception:
                    translations[code] = {}

    def get_text(key, default=None):
        lang = g.get("lang", "en")
        parts = key.split(".")
        val = translations.get(lang, {})
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                val = None
                break
        if val is None:
            # fallback to english
            val = translations.get("en", {})
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
                    break
        return val if val is not None else (default if default is not None else key)

    # ── Supported languages before-request ──────────────────────────────────
    @app.before_request
    def set_language():
        lang = (
            request.args.get("lang")
            or session.get("lang")
            or app.config["DEFAULT_LANGUAGE"]
        )
        if lang not in app.config["SUPPORTED_LANGUAGES"]:
            lang = app.config["DEFAULT_LANGUAGE"]
        g.lang = lang
        session["lang"] = lang

    # ── Security Headers ─────────────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

    # ── Inject globals into all templates ───────────────────────────────────
    @app.context_processor
    def inject_globals():
        is_demo = (
            request.args.get("demo") in ("1", "true") or
            session.get("demo_mode") is True or
            app.config.get("DEMO_MODE", False) is True
        )
        return {
            "app_name": app.config["APP_NAME"],
            "app_tagline": app.config["APP_TAGLINE"],
            "app_version": app.config["APP_VERSION"],
            "current_lang": g.get("lang", "en"),
            "supported_languages": app.config["SUPPORTED_LANGUAGES"],
            "future_languages": app.config["FUTURE_LANGUAGES"],
            "is_demo_mode": is_demo,
            "t": get_text,
        }

    # ── Register blueprints ──────────────────────────────────────────────────
    from app.web.main import main_bp
    from app.web.policies import policies_bp
    from app.web.search import search_bp, ai_chat_bp, monitor_bp, settings_bp
    from app.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(policies_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(ai_chat_bp)
    app.register_blueprint(monitor_bp)
    app.register_blueprint(settings_bp)

    # Primary /api prefix + /api/v1 compatibility
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(api_bp, url_prefix="/api/v1", name="api_v1")

    # ── Error handlers ───────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # ── Auto-create tables & seed database ───────────────────────────────────
    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        _ensure_schema_columns(db.engine)
        from app.models import PolicyDocument
        if PolicyDocument.query.count() == 0:
            from app.database_seeder import seed_database
            seed_database()

    return app


def _ensure_schema_columns(engine):
    """Safely add new validation and tracking columns if missing in existing SQLite databases."""
    try:
        from sqlalchemy import text
        if engine.dialect.name != "sqlite":
            return
        with engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(policy_documents)")).fetchall()]
            if cols:
                if "official_url" not in cols:
                    conn.execute(text("ALTER TABLE policy_documents ADD COLUMN official_url VARCHAR(1024)"))
                if "source_listing_url" not in cols:
                    conn.execute(text("ALTER TABLE policy_documents ADD COLUMN source_listing_url VARCHAR(1024)"))
                if "first_detected_at" not in cols:
                    conn.execute(text("ALTER TABLE policy_documents ADD COLUMN first_detected_at DATETIME"))
                if "current_version" not in cols:
                    conn.execute(text("ALTER TABLE policy_documents ADD COLUMN current_version INTEGER NOT NULL DEFAULT 1"))
                if "is_verified" not in cols:
                    conn.execute(text("ALTER TABLE policy_documents ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 1"))
                if "classification_status" not in cols:
                    conn.execute(text("ALTER TABLE policy_documents ADD COLUMN classification_status VARCHAR(50) NOT NULL DEFAULT 'verified_policy'"))
                conn.commit()
    except Exception:
        pass
