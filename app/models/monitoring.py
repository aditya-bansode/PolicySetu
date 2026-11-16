"""
PolicySetu — MonitoringLog Model
================================
Tracks automated crawler execution logs, statuses, and performance timings.
"""

from app.extensions import db
from app.utils.helpers import utc_now, format_datetime_local


class MonitoringLog(db.Model):
    __tablename__ = "monitoring_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, db.ForeignKey("government_sources.id", ondelete="CASCADE"), nullable=True, index=True)
    checked_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    status = db.Column(db.String(50), nullable=False, default="success", index=True)  # success, failed, warning
    documents_found = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)
    execution_time = db.Column(db.Float, nullable=False, default=0.0)  # in seconds

    # Relationships
    source = db.relationship("GovernmentSource", back_populates="monitoring_logs")

    def to_dict(self, tz: str = "Asia/Kolkata") -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source.name if self.source else None,
            "checked_at": format_datetime_local(self.checked_at, tz_name=tz),
            "status": self.status,
            "documents_found": self.documents_found,
            "error_message": self.error_message,
            "execution_time": round(self.execution_time, 2),
        }
