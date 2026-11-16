"""
PolicySetu — GovernmentSource Model
===================================
Tracks government portals, gazette sites, and departments monitored by the system.
"""

from app.extensions import db
from app.utils.helpers import utc_now, format_datetime_local


class GovernmentSource(db.Model):
    __tablename__ = "government_sources"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    base_url = db.Column(db.String(1024), nullable=False)
    jurisdiction = db.Column(db.String(100), nullable=False, default="Central Government", index=True)
    state = db.Column(db.String(100), nullable=True, index=True)
    department = db.Column(db.String(255), nullable=True)
    source_type = db.Column(db.String(50), nullable=False, default="portal")  # e.g., portal, pib, gazette, api
    enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    last_checked_at = db.Column(db.DateTime, nullable=True)
    last_success_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    documents = db.relationship("PolicyDocument", back_populates="source", cascade="all, delete-orphan", lazy="dynamic")
    monitoring_logs = db.relationship("MonitoringLog", back_populates="source", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self, tz: str = "Asia/Kolkata") -> dict:
        if not self.enabled:
            status_val = "inaccessible"
        elif self.last_error:
            status_val = "degraded"
        else:
            status_val = "active"
        doc_count = self.documents.count() if hasattr(self, "documents") else 0

        last_chk = format_datetime_local(self.last_checked_at, tz_name=tz)
        last_succ = format_datetime_local(self.last_success_at, tz_name=tz)
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "url": self.base_url,
            "jurisdiction": self.jurisdiction,
            "state": self.state,
            "department": self.department,
            "source_type": self.source_type,
            "enabled": self.enabled,
            "status": status_val,
            "last_checked_at": last_chk,
            "last_checked": last_chk or "Never",
            "last_success_at": last_succ,
            "last_success": last_succ or "Never",
            "last_error": self.last_error,
            "created_at": format_datetime_local(self.created_at, tz_name=tz),
            "documents_count": doc_count,
            "policies_count": doc_count,
            "crawl_interval_hours": 24,
        }

