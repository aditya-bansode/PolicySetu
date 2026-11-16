"""PolicySetu API — Demo data for policies endpoints."""
from flask import jsonify, request
from app.api import api_v1_bp
from app.demo_data import DEMO_POLICIES, DEMO_CATEGORIES


@api_v1_bp.route("/policies")
def list_policies():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 12))
    category = request.args.get("category", "")
    policy_type = request.args.get("type", "")
    state = request.args.get("state", "")
    q = request.args.get("q", "").lower()

    filtered = DEMO_POLICIES[:]
    if category:
        filtered = [p for p in filtered if p.get("category", "").lower() == category.lower()]
    if policy_type:
        filtered = [p for p in filtered if p.get("type", "").lower() == policy_type.lower()]
    if state:
        filtered = [p for p in filtered if p.get("jurisdiction", "").lower() == state.lower()]
    if q:
        filtered = [p for p in filtered if q in p.get("title", "").lower() or q in p.get("summary", "").lower()]

    sort = request.args.get("sort", "date_desc")
    if sort == "date_asc":
        filtered.sort(key=lambda x: x.get("published_date", ""))
    elif sort == "popular":
        filtered.sort(key=lambda x: x.get("view_count", 0), reverse=True)
    else:
        filtered.sort(key=lambda x: x.get("published_date", ""), reverse=True)

    total = len(filtered)
    start = (page - 1) * per_page
    items = filtered[start: start + per_page]

    return jsonify({
        "success": True,
        "data": items,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, -(-total // per_page)),
            "is_demo": True,
        }
    })


@api_v1_bp.route("/policies/<int:policy_id>")
def get_policy(policy_id):
    policy = next((p for p in DEMO_POLICIES if p["id"] == policy_id), None)
    if not policy:
        return jsonify({"success": False, "error": "Policy not found"}), 404
    return jsonify({"success": True, "data": policy, "meta": {"is_demo": True}})


@api_v1_bp.route("/policies/<int:policy_id>/versions")
def get_policy_versions(policy_id):
    from app.demo_data import DEMO_VERSIONS
    versions = [v for v in DEMO_VERSIONS if v["policy_id"] == policy_id]
    return jsonify({"success": True, "data": versions, "meta": {"is_demo": True}})


@api_v1_bp.route("/categories")
def list_categories():
    return jsonify({"success": True, "data": DEMO_CATEGORIES, "meta": {"is_demo": True}})
