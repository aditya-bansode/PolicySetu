"""PolicySetu API — Search endpoint."""
from flask import jsonify, request
from app.api import api_v1_bp
from app.demo_data import DEMO_POLICIES


@api_v1_bp.route("/search")
def search():
    q = request.args.get("q", "").lower().strip()
    if not q:
        return jsonify({"success": True, "data": [], "meta": {"total": 0, "is_demo": True}})

    results = []
    for p in DEMO_POLICIES:
        score = 0
        title = p.get("title", "").lower()
        summary = p.get("summary", "").lower()
        ministry = p.get("ministry", "").lower()
        if q in title:
            score += 10
        if q in summary:
            score += 5
        if q in ministry:
            score += 3
        if score > 0:
            result = dict(p)
            result["score"] = score
            # Highlight snippet
            if q in summary:
                idx = summary.find(q)
                snippet = p["summary"][max(0, idx - 60): idx + 120]
                result["snippet"] = f"...{snippet}..."
            else:
                result["snippet"] = p.get("summary", "")[:180] + "..."
            results.append(result)

    results.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({
        "success": True,
        "data": results,
        "meta": {"total": len(results), "query": q, "is_demo": True}
    })
