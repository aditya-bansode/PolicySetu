"""
PolicySetu — PolicyAnalysis Model
=================================
Stores multilingual summaries (EN, HI, MR), extracted key provisions,
important dates, eligibility conditions, and affected stakeholder groups.
"""

import json
from app.extensions import db
from app.utils.helpers import utc_now, format_datetime_local


class PolicyAnalysis(db.Model):
    __tablename__ = "policy_analyses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_id = db.Column(db.Integer, db.ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    summary_en = db.Column(db.Text, nullable=True)
    summary_mr = db.Column(db.Text, nullable=True)
    summary_hi = db.Column(db.Text, nullable=True)
    key_provisions = db.Column(db.Text, nullable=True)     # JSON array string
    important_dates = db.Column(db.Text, nullable=True)    # JSON object string
    conditions = db.Column(db.Text, nullable=True)         # JSON array or text
    affected_groups = db.Column(db.Text, nullable=True)    # JSON object {group: description}
    confidence_score = db.Column(db.Float, nullable=False, default=0.95)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    document = db.relationship("PolicyDocument", back_populates="analysis")

    def get_key_provisions_list(self) -> list:
        if not self.key_provisions:
            return []
        try:
            return json.loads(self.key_provisions)
        except Exception:
            return [self.key_provisions]

    def get_important_dates_dict(self) -> dict:
        if not self.important_dates:
            return {}
        try:
            return json.loads(self.important_dates)
        except Exception:
            return {}

    def get_affected_groups_dict(self) -> dict:
        if not self.affected_groups:
            return {}
        try:
            return json.loads(self.affected_groups)
        except Exception:
            return {}

    def to_dict(self, tz: str = "Asia/Kolkata") -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "summary_en": self.summary_en,
            "summary_mr": self.summary_mr,
            "summary_hi": self.summary_hi,
            "key_provisions": self.get_key_provisions_list(),
            "important_dates": self.get_important_dates_dict(),
            "conditions": self.conditions,
            "affected_groups": self.get_affected_groups_dict(),
            "confidence_score": self.confidence_score,
            "created_at": format_datetime_local(self.created_at, tz_name=tz),
        }
