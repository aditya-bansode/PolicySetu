"""
PolicySetu — MonitoringService
==============================
Business logic for crawler execution logs and source health metrics.
"""

from app.models import MonitoringLog, GovernmentSource
from app.extensions import db
from app.utils.helpers import utc_now
from app.utils.pagination import paginate_query


class MonitoringService:
    @staticmethod
    def get_logs(source_id: int | None = None, page: int = 1, per_page: int = 10):
        """Retrieve paginated monitoring logs."""
        query = MonitoringLog.query.order_by(MonitoringLog.checked_at.desc())
        if source_id:
            query = query.filter_by(source_id=source_id)

        items, meta = paginate_query(query, page=page, per_page=per_page)
        return [log.to_dict() for log in items], meta

    @staticmethod
    def record_log(source_id: int, status: str, documents_found: int, error_message: str | None, execution_time: float):
        """Record a new crawler monitoring check in the database."""
        log = MonitoringLog(
            source_id=source_id,
            checked_at=utc_now(),
            status=status,
            documents_found=documents_found,
            error_message=error_message,
            execution_time=execution_time
        )
        db.session.add(log)

        # Update source
        source = GovernmentSource.query.get(source_id)
        if source:
            source.last_checked_at = log.checked_at
            if status == "success":
                source.last_success_at = log.checked_at
                source.last_error = None
            else:
                source.last_error = error_message

        db.session.commit()
        return log
