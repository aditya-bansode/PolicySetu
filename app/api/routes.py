"""
PolicySetu — API Routes Module
==============================
Implements all required REST API endpoints with pagination, validation,
error handling, and consistent JSON response envelopes.
"""

from flask import Blueprint, request
from sqlalchemy import text
from app.extensions import db
from app.services.policy_service import PolicyService
from app.services.source_service import SourceService
from app.services.category_service import CategoryService
from app.services.monitoring_service import MonitoringService
from app.services.monitoring_engine import PolicyMonitoringEngine
from app.services.ai_service import AIService
from app.services.scholarship_service import ScholarshipService
from app.utils.helpers import api_response, utc_now
from app.utils.pagination import get_pagination_params
from app.utils.rate_limiter import rate_limit


api_bp = Blueprint("api", __name__)


# ── Error Handlers ────────────────────────────────────────────────────────────
@api_bp.errorhandler(404)
def resource_not_found(e):
    return api_response(success=False, error="Resource not found", status_code=404)


@api_bp.errorhandler(400)
def bad_request(e):
    return api_response(success=False, error="Bad request parameter", status_code=400)


@api_bp.errorhandler(500)
def internal_server_error(e):
    return api_response(success=False, error="Internal server error", status_code=500)


# ── 1. GET /api/health ────────────────────────────────────────────────────────
@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint verifying database connectivity and service state."""
    db_status = "connected"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    is_healthy = db_status == "connected"
    return api_response(
        data={
            "status": "healthy" if is_healthy else "unhealthy",
            "database": db_status,
            "timestamp": utc_now().isoformat() + "Z",
            "version": "1.0.0-beta",
            "service": "PolicySetu Backend"
        },
        success=is_healthy,
        status_code=200 if is_healthy else 503
    )


# ── 2. GET /api/dashboard/stats ───────────────────────────────────────────────
@api_bp.route("/dashboard/stats", methods=["GET"])
@rate_limit(requests_per_minute=60)
def dashboard_stats():
    """Live summary statistics for policies, active sources, and distributions."""
    try:
        stats = PolicyService.get_dashboard_stats()
        return api_response(data=stats)
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# Sub-routes for granular frontend chart queries
@api_bp.route("/stats/categories", methods=["GET"])
def stats_categories():
    stats = PolicyService.get_dashboard_stats()
    return api_response(data=stats["categories"])


@api_bp.route("/stats/jurisdictions", methods=["GET"])
def stats_jurisdictions():
    stats = PolicyService.get_dashboard_stats()
    return api_response(data=stats["jurisdictions"])


@api_bp.route("/stats/timeline", methods=["GET"])
def stats_timeline():
    """Live 6-month publication timeline from official database records."""
    stats = PolicyService.get_dashboard_stats()
    return api_response(data=stats.get("timeline", []))


@api_bp.route("/stats/sources", methods=["GET"])
def stats_sources():
    sources = SourceService.get_sources()
    return api_response(data=sources)


# ── 3. GET /api/policies ──────────────────────────────────────────────────────
@api_bp.route("/policies", methods=["GET"])
@rate_limit(requests_per_minute=60)
def list_policies():
    """Paginated, filtered list of government policies."""
    page, per_page = get_pagination_params(default_per_page=12, max_per_page=50)
    lang = request.args.get("lang", "en")

    filters = {
        "q": request.args.get("q", ""),
        "category": request.args.get("category", ""),
        "type": request.args.get("type", "") or request.args.get("document_type", ""),
        "state": request.args.get("state", "") or request.args.get("jurisdiction", ""),
        "sort": request.args.get("sort", "date_desc"),
        "status": request.args.get("status", "all"),
        "is_new": request.args.get("is_new"),
        "is_modified": request.args.get("is_modified"),
    }

    try:
        policies, meta = PolicyService.get_policies(filters=filters, page=page, per_page=per_page, lang=lang)
        return api_response(data=policies, meta=meta)
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# ── 3b. GET /api/search ───────────────────────────────────────────────────────
@api_bp.route("/search", methods=["GET"])
@rate_limit(requests_per_minute=60)
def search_policies():
    """Live full-text and keyword search across government policies."""
    q = request.args.get("q", "").strip()
    page, per_page = get_pagination_params(default_per_page=12, max_per_page=50)
    lang = request.args.get("lang", "en")

    if not q:
        return api_response(data=[], meta={"page": 1, "per_page": per_page, "total": 0, "query": ""})

    filters = {
        "q": q,
        "category": request.args.get("category", ""),
        "type": request.args.get("type", "") or request.args.get("document_type", ""),
        "state": request.args.get("state", "") or request.args.get("jurisdiction", ""),
        "sort": request.args.get("sort", "date_desc"),
        "status": request.args.get("status", "all"),
    }

    try:
        policies, meta = PolicyService.get_policies(filters=filters, page=page, per_page=per_page, lang=lang)
        return api_response(data=policies, meta=meta)
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# ── 4. GET /api/policies/<id> ─────────────────────────────────────────────────
@api_bp.route("/policies/<int:policy_id>", methods=["GET"])
def get_policy(policy_id: int):
    """Retrieve full details of a single policy document."""
    lang = request.args.get("lang", "en")
    policy = PolicyService.get_by_id(policy_id, lang=lang, include_content=True)
    if not policy:
        return api_response(success=False, error=f"Policy with ID {policy_id} not found", status_code=404)
    return api_response(data=policy)


# ── 5. GET /api/policies/<id>/versions ────────────────────────────────────────
@api_bp.route("/policies/<int:policy_id>/versions", methods=["GET"])
def get_policy_versions(policy_id: int):
    """Retrieve all recorded versions of a policy document."""
    doc = PolicyService.get_by_id(policy_id)
    if not doc:
        return api_response(success=False, error=f"Policy with ID {policy_id} not found", status_code=404)

    versions = PolicyService.get_versions(policy_id)
    return api_response(data=versions)


# ── 6. GET /api/policies/<id>/changes ─────────────────────────────────────────
@api_bp.route("/policies/<int:policy_id>/changes", methods=["GET"])
def get_policy_changes(policy_id: int):
    """Retrieve all change events recorded for a policy document."""
    doc = PolicyService.get_by_id(policy_id)
    if not doc:
        return api_response(success=False, error=f"Policy with ID {policy_id} not found", status_code=404)

    changes = PolicyService.get_changes(policy_id)
    return api_response(data=changes)


# ── 7. GET /api/categories ────────────────────────────────────────────────────
@api_bp.route("/categories", methods=["GET"])
def get_categories():
    """Retrieve all policy categories in the specified language."""
    lang = request.args.get("lang", "en")
    categories = CategoryService.get_categories(lang=lang)
    return api_response(data=categories)


# ── 8. GET /api/sources ───────────────────────────────────────────────────────
@api_bp.route("/sources", methods=["GET"])
def get_sources():
    """Retrieve all monitored government portals and sources."""
    enabled_only = request.args.get("enabled") in ("1", "true", "True")
    jurisdiction = request.args.get("jurisdiction")
    sources = SourceService.get_sources(enabled_only=enabled_only, jurisdiction=jurisdiction)
    return api_response(data=sources)


# ── 9. GET /api/monitoring/logs ───────────────────────────────────────────────
@api_bp.route("/monitoring/logs", methods=["GET"])
def get_monitoring_logs():
    """Retrieve paginated automated crawler logs."""
    page, per_page = get_pagination_params(default_per_page=10, max_per_page=50)
    source_id = request.args.get("source_id", type=int)
    logs, meta = MonitoringService.get_logs(source_id=source_id, page=page, per_page=per_page)
    return api_response(data=logs, meta=meta)


@api_bp.route("/monitoring/scan", methods=["POST"])
def trigger_monitoring_scan():
    """Trigger an immediate on-demand policy monitoring cycle across all sources."""
    try:
        engine = PolicyMonitoringEngine()
        summary = engine.scan_all_sources(max_items_per_source=10)
        return api_response(data=summary)
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


@api_bp.route("/monitoring/sources/<int:source_id>/scan", methods=["POST"])
def trigger_single_source_scan(source_id: int):
    """Trigger on-demand scan for a single verified government source."""
    try:
        engine = PolicyMonitoringEngine()
        result = engine.scan_source(source_id, max_items=10)
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)



# ── 10. POST /api/policies/<id>/compare ───────────────────────────────────────
@api_bp.route("/policies/<int:policy_id>/compare", methods=["POST"])
def compare_policy_versions(policy_id: int):
    """Compare two versions of a policy document."""
    body = request.get_json(silent=True) or {}
    try:
        v1 = int(body.get("v1") or request.args.get("v1", 1))
        v2 = int(body.get("v2") or request.args.get("v2", 2))
    except (ValueError, TypeError):
        return api_response(success=False, error="Invalid version numbers provided. Must be integers.", status_code=400)

    comparison = PolicyService.compare_versions(policy_id=policy_id, v1_num=v1, v2_num=v2)
    if not comparison:
        return api_response(success=False, error=f"Versions {v1} or {v2} for policy {policy_id} not found", status_code=404)

    return api_response(data=comparison)


# ── 11. POST /api/ai/ask ──────────────────────────────────────────────────────
@api_bp.route("/ai/ask", methods=["POST"])
@api_bp.route("/ask", methods=["POST"])  # backward-compatibility
@rate_limit(requests_per_minute=30)
def ai_ask():
    """RAG-based question answering grounded in official government policy documents."""
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    if not question:
        return api_response(success=False, error="Parameter 'question' is required and cannot be empty.", status_code=400)

    language = body.get("language") or request.args.get("lang") or "en"
    history = body.get("conversation_history", [])

    try:
        response = AIService.ask(question=question, language=language, history=history)
        return api_response(data=response)
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# ── 12. POST /api/ai/summarize ────────────────────────────────────────────────
@api_bp.route("/ai/summarize", methods=["POST"])
@api_bp.route("/ai/summarize/<int:policy_id>", methods=["POST"])
@api_bp.route("/summarize/<int:policy_id>", methods=["POST"])  # backward-compatibility
@rate_limit(requests_per_minute=30)
def ai_summarize(policy_id: int | None = None):
    """Summarize a policy document in English, Hindi, or Marathi."""
    body = request.get_json(silent=True) or {}
    pid = policy_id or body.get("policy_id") or request.args.get("policy_id", type=int)

    if not pid:
        return api_response(success=False, error="Parameter 'policy_id' is required.", status_code=400)

    language = body.get("language") or request.args.get("lang") or "en"

    summary_data = AIService.summarize(policy_id=int(pid), language=language)
    if not summary_data:
        return api_response(success=False, error=f"Policy with ID {pid} not found.", status_code=404)

    return api_response(data=summary_data)


# ── 13. GET /api/scholarships ─────────────────────────────────────────────────
@api_bp.route("/scholarships", methods=["GET"])
def get_scholarships():
    """Retrieve verified Maharashtra MahaDBT scholarship schemes."""
    q = request.args.get("q", "").strip()
    dept = request.args.get("department", "").strip()
    limit = min(request.args.get("limit", 50, type=int), 100)

    try:
        schemes = ScholarshipService.get_scholarships(query=q, department=dept, limit=limit)
        return api_response(data=schemes, meta={"count": len(schemes), "academic_year": "2026-27"})
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# ── 14. GET /api/scholarships/<id> ───────────────────────────────────────────
@api_bp.route("/scholarships/<int:scholarship_id>", methods=["GET"])
def get_scholarship_by_id(scholarship_id: int):
    """Retrieve details of a single MahaDBT scholarship scheme."""
    sch = ScholarshipService.get_by_id(scholarship_id)
    if not sch:
        return api_response(success=False, error=f"Scholarship scheme with ID {scholarship_id} not found", status_code=404)
    return api_response(data=sch)


# ── 15. POST /api/scholarships/import ─────────────────────────────────────────
@api_bp.route("/scholarships/import", methods=["POST"])
def import_verified_scholarships():
    """Admin-assisted import and verification of official MahaDBT scholarship schemes."""
    body = request.get_json(silent=True) or {}
    custom_scheme = body.get("scheme")

    try:
        if custom_scheme and isinstance(custom_scheme, dict) and custom_scheme.get("scheme_name"):
            sch, doc, is_new = ScholarshipService.import_or_update_scholarship(custom_scheme)
            return api_response(data={"message": "Scheme imported successfully", "scheme": sch.to_dict(), "is_new": is_new})
        else:
            result = ScholarshipService.seed_all_verified_scholarships()
            return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# ── 16. POST /api/scholarships/sync ───────────────────────────────────────────
@api_bp.route("/scholarships/sync", methods=["POST"])
def sync_scholarships_from_portal():
    """Trigger source adapter sync from live MahaDBT and MahaDBT 2.0 portals."""
    try:
        from app.adapters.mahadbt_adapter import MahaDBTAdapter
        adapter = MahaDBTAdapter()
        raw_schemes = adapter.fetch_recent_documents(limit=50)

        synced_count = 0
        for item in raw_schemes:
            sch, doc, is_new = ScholarshipService.import_or_update_scholarship(item)
            synced_count += 1

        return api_response(data={
            "status": "success",
            "crawled_count": len(raw_schemes),
            "synced_count": synced_count,
            "academic_year": "2026-27",
            "portal": "https://mahadbt2.maharashtra.gov.in"
        })
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)
