"""
PolicySetu — API Package
========================
Exports the unified REST API blueprint.
"""

from app.api.routes import api_bp

__all__ = ["api_bp"]
