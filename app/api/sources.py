"""PolicySetu API — Government sources endpoint."""
from flask import jsonify
from app.api import api_v1_bp
from app.demo_data import DEMO_SOURCES


@api_v1_bp.route("/sources")
def list_sources():
    return jsonify({"success": True, "data": DEMO_SOURCES, "meta": {"is_demo": True}})


@api_v1_bp.route("/sources/<int:source_id>/logs")
def source_logs(source_id):
    from app.demo_data import DEMO_CRAWL_LOGS
    logs = [l for l in DEMO_CRAWL_LOGS if l["source_id"] == source_id]
    return jsonify({"success": True, "data": logs, "meta": {"is_demo": True}})
