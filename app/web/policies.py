"""
PolicySetu Web — Policies routes.
Powered by PolicyService, DocumentVersion, and database models.
"""

from flask import Blueprint, render_template, request, abort, g
from app.services.policy_service import PolicyService
from app.services.category_service import CategoryService
from app.models import DocumentVersion

policies_bp = Blueprint("policies", __name__)


@policies_bp.route("/policies")
def list_policies():
    lang = g.get("lang", "en")
    categories = CategoryService.get_categories(lang=lang)
    return render_template(
        "pages/policy_list.html",
        categories=categories,
        active_page="policies",
    )


@policies_bp.route("/policies/<int:policy_id>")
def policy_detail(policy_id):
    lang = g.get("lang", "en")
    policy = PolicyService.get_by_id(policy_id, lang=lang, include_content=True)
    if not policy:
        abort(404)
    versions = PolicyService.get_versions(policy_id)
    return render_template(
        "pages/policy_detail.html",
        policy=policy,
        versions=versions,
        active_page="policies",
    )


@policies_bp.route("/policies/<int:policy_id>/compare")
def policy_compare(policy_id):
    lang = g.get("lang", "en")
    policy = PolicyService.get_by_id(policy_id, lang=lang, include_content=True)
    if not policy:
        abort(404)

    versions = PolicyService.get_versions(policy_id)
    try:
        v1_num = int(request.args.get("v1", 1))
        v2_num = int(request.args.get("v2", 2))
    except (ValueError, TypeError):
        v1_num, v2_num = 1, 2

    comparison = PolicyService.compare_versions(policy_id, v1_num, v2_num)
    v1 = next((v for v in versions if v["version_number"] == v1_num), None)
    v2 = next((v for v in versions if v["version_number"] == v2_num), None)

    if comparison and v2:
        v2["diff_summary"] = comparison.get("diff_summary")
        v2["changed_sections"] = comparison.get("changed_sections", [])
        v2["modified_clauses"] = comparison.get("modified_clauses", [])
        v2["added_clauses"] = comparison.get("added_clauses", [])
        v2["removed_clauses"] = comparison.get("removed_clauses", [])
        v2["added_text"] = " ".join([c["text"] for c in comparison.get("added_clauses", [])])

    if v1:
        v1["raw_text_excerpt"] = (v1.get("content") or "")[:400]
    if v2:
        v2["raw_text_excerpt"] = (v2.get("content") or "")[:400]

    return render_template(
        "pages/policy_compare.html",
        policy=policy,
        versions=versions,
        v1=v1,
        v2=v2,
        comparison=comparison,
        active_page="policies",
    )



@policies_bp.route("/policies/<int:policy_id>/impact")
def policy_impact(policy_id):
    lang = g.get("lang", "en")
    policy = PolicyService.get_by_id(policy_id, lang=lang, include_content=True)
    if not policy:
        abort(404)
    return render_template(
        "pages/policy_impact.html",
        policy=policy,
        active_page="policies",
    )
