"""
PolicySetu Web — Search, AI Chat, Monitor, Settings routes.
Powered by CategoryService, SourceService, and MonitoringService.
"""

from flask import Blueprint, render_template, g
from app.services.category_service import CategoryService
from app.services.source_service import SourceService
from app.services.monitoring_service import MonitoringService
from app.demo_data import (
    DEMO_AI_QUESTIONS, DEMO_AI_QUESTIONS_HI, DEMO_AI_QUESTIONS_MR
)

# Search
search_bp = Blueprint("search", __name__)

@search_bp.route("/search")
def search():
    lang = g.get("lang", "en")
    categories = CategoryService.get_categories(lang=lang)
    return render_template("pages/search.html", categories=categories, active_page="search")


# AI Chat
ai_chat_bp = Blueprint("ai_chat", __name__)

@ai_chat_bp.route("/ask")
def ask():
    lang = g.get("lang", "en")
    if lang == "hi":
        questions = DEMO_AI_QUESTIONS_HI
    elif lang == "mr":
        questions = DEMO_AI_QUESTIONS_MR
    else:
        questions = DEMO_AI_QUESTIONS
    return render_template("pages/ask_ai.html", suggested_questions=questions, active_page="ask")


# Monitor
monitor_bp = Blueprint("monitor", __name__)

@monitor_bp.route("/monitor")
def monitor():
    sources = SourceService.get_sources()
    logs, _ = MonitoringService.get_logs(page=1, per_page=10)
    return render_template("pages/monitor.html", sources=sources, crawl_logs=logs, active_page="monitor")


# Settings
settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings")
def settings():
    return render_template("pages/settings.html", active_page="settings")
