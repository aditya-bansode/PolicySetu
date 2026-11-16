"""
PolicySetu — Pagination Utility
===============================
Standard pagination helper for SQLAlchemy queries.
"""

from math import ceil
from flask import request


def get_pagination_params(default_per_page: int = 10, max_per_page: int = 50):
    """Extract page and per_page from request query parameters safely."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = int(request.args.get("per_page", default_per_page))
        per_page = max(1, min(per_page, max_per_page))
    except (ValueError, TypeError):
        per_page = default_per_page

    return page, per_page


def paginate_query(query, page: int = 1, per_page: int = 10):
    """
    Paginate a SQLAlchemy query and return items list and standard metadata dictionary.
    """
    total = query.count()
    total_pages = ceil(total / per_page) if per_page > 0 else 1
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1

    offset = (page - 1) * per_page
    items = query.limit(per_page).offset(offset).all()

    meta = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
    return items, meta
