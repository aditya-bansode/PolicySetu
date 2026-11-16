"""
PolicySetu Web — Main routes (home, about).
Powered by PolicyService, SourceService, and database models.
"""

from flask import Blueprint, render_template, g
from app.services.policy_service import PolicyService
from app.services.source_service import SourceService
from app.services.category_service import CategoryService

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    lang = g.get("lang", "en")
    stats = PolicyService.get_dashboard_stats()
    recent_policies, _ = PolicyService.get_policies(filters={"sort": "date_desc"}, page=1, per_page=6, lang=lang)
    new_policies, _ = PolicyService.get_policies(filters={"is_new": True}, page=1, per_page=6, lang=lang)
    modified_policies, _ = PolicyService.get_policies(filters={"is_modified": True}, page=1, per_page=6, lang=lang)
    sources = SourceService.get_sources()
    categories = CategoryService.get_categories(lang=lang)

    return render_template(
        "pages/home.html",
        new_policies=new_policies,
        modified_policies=modified_policies,
        recent_policies=recent_policies,
        sources=sources,
        categories=categories,
        total_policies=stats["total_policies"],
        new_count=stats["new_this_week"],
        modified_count=stats["modified_policies"],
        active_sources=stats["active_sources"],
        active_page="home",
    )


@main_bp.route("/about")
def about():
    return render_template("pages/about.html", active_page="about")
