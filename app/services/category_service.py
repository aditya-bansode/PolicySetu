"""
PolicySetu — CategoryService
============================
Business logic for multilingual policy categories.
"""

from app.models import PolicyCategory
from app.extensions import db


class CategoryService:
    @staticmethod
    def get_categories(lang: str = "en"):
        """Retrieve all policy categories localized in the specified language."""
        categories = PolicyCategory.query.order_by(PolicyCategory.id.asc()).all()
        return [c.to_dict(lang=lang) for c in categories]

    @staticmethod
    def get_by_id(category_id: int, lang: str = "en"):
        """Get a single category by ID."""
        cat = db.session.get(PolicyCategory, category_id)
        return cat.to_dict(lang=lang) if cat else None
