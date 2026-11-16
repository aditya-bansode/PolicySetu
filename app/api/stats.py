"""PolicySetu API — Stats endpoint for Chart.js dashboard."""
from flask import jsonify
from app.api import api_v1_bp
from app.demo_data import DEMO_POLICIES, DEMO_SOURCES, DEMO_CATEGORIES


@api_v1_bp.route("/stats/overview")
def stats_overview():
    new_count = sum(1 for p in DEMO_POLICIES if p.get("is_new"))
    modified_count = sum(1 for p in DEMO_POLICIES if p.get("is_modified"))
    active_sources = sum(1 for s in DEMO_SOURCES if s.get("status") == "active")
    return jsonify({
        "success": True,
        "data": {
            "total_policies": len(DEMO_POLICIES),
            "new_policies": new_count,
            "modified_policies": modified_count,
            "active_sources": active_sources,
            "total_sources": len(DEMO_SOURCES),
            "is_demo": True,
        }
    })


@api_v1_bp.route("/stats/categories")
def stats_categories():
    counts = {}
    for p in DEMO_POLICIES:
        cat = p.get("category", "Other")
        counts[cat] = counts.get(cat, 0) + 1
    result = [{"category": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    return jsonify({"success": True, "data": result, "meta": {"is_demo": True}})


@api_v1_bp.route("/stats/timeline")
def stats_timeline():
    from collections import Counter
    dates = [p["published_date"][:7] for p in DEMO_POLICIES if p.get("published_date")]
    counts = Counter(dates)
    result = [{"month": k, "count": v} for k, v in sorted(counts.items())]
    return jsonify({"success": True, "data": result, "meta": {"is_demo": True}})


@api_v1_bp.route("/stats/sources")
def stats_sources():
    result = [
        {
            "name": s["name"],
            "status": s["status"],
            "policies_count": s.get("policies_count", 0),
        }
        for s in DEMO_SOURCES
    ]
    return jsonify({"success": True, "data": result, "meta": {"is_demo": True}})


@api_v1_bp.route("/stats/jurisdictions")
def stats_jurisdictions():
    counts = {}
    for p in DEMO_POLICIES:
        j = p.get("jurisdiction", "Other")
        counts[j] = counts.get(j, 0) + 1
    result = [{"jurisdiction": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    return jsonify({"success": True, "data": result, "meta": {"is_demo": True}})
