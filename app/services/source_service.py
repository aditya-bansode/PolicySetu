"""
PolicySetu — SourceService
==========================
Business logic for managing and querying monitored Government sources.
"""

from app.models import GovernmentSource
from app.extensions import db
from app.utils.helpers import utc_now


class SourceService:
    @staticmethod
    def get_sources(enabled_only: bool = False, jurisdiction: str | None = None):
        """List all monitored government sources."""
        query = GovernmentSource.query
        if enabled_only:
            query = query.filter_by(enabled=True)
        if jurisdiction:
            query = query.filter(GovernmentSource.jurisdiction.ilike(f"%{jurisdiction.strip()}%"))
        sources = query.order_by(GovernmentSource.id.asc()).all()
        return [s.to_dict() for s in sources]

    @staticmethod
    def get_source_by_id(source_id: int):
        """Retrieve a specific government source by ID."""
        source = db.session.get(GovernmentSource, source_id)
        return source.to_dict() if source else None

    @staticmethod
    def update_source_status(source_id: int, status: str, error_message: str | None = None):
        """Update last checked and status timestamp for a source."""
        source = db.session.get(GovernmentSource, source_id)
        if not source:
            return None
        source.last_checked_at = utc_now()
        if status == "success":
            source.last_success_at = utc_now()
            source.last_error = None
        else:
            source.last_error = error_message
        db.session.commit()
        return source
