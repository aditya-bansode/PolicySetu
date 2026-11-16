"""
PolicySetu — ScholarshipScheme Model
====================================
Tracks verified Maharashtra MahaDBT scholarship schemes, eligibility conditions,
academic year designations, benefit details, and official government portal links.
"""

from app.extensions import db
from app.utils.helpers import utc_now, format_datetime_local


class ScholarshipScheme(db.Model):
    __tablename__ = "scholarship_schemes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scheme_name = db.Column(db.String(500), nullable=False, unique=True, index=True)
    department = db.Column(db.String(255), nullable=True, index=True)
    jurisdiction = db.Column(db.String(100), nullable=False, default="Maharashtra", index=True)
    category = db.Column(db.String(100), nullable=False, default="Education", index=True)
    description = db.Column(db.Text, nullable=True)
    eligibility_criteria = db.Column(db.Text, nullable=True)
    income_limit = db.Column(db.String(255), nullable=True)
    caste_category = db.Column(db.String(255), nullable=True)
    course_criteria = db.Column(db.String(255), nullable=True)
    benefit_details = db.Column(db.Text, nullable=True)
    required_documents = db.Column(db.Text, nullable=True)
    application_start_date = db.Column(db.Date, nullable=True)
    application_end_date = db.Column(db.Date, nullable=True)
    academic_year = db.Column(db.String(50), nullable=True, default="2026-27")
    application_status = db.Column(db.String(100), nullable=True, default="Active (AY 2026-27 on MahaDBT 2.0)")
    official_scheme_url = db.Column(db.String(1024), nullable=True)
    official_guidelines_url = db.Column(db.String(1024), nullable=True)
    source_name = db.Column(db.String(255), nullable=True, default="MahaDBT (Government of Maharashtra)")
    last_verified_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    verification_status = db.Column(db.Boolean, nullable=False, default=True)

    # Relationship to PolicyDocument for unified discovery
    policy_document_id = db.Column(db.Integer, db.ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=True, index=True)
    policy_document = db.relationship("PolicyDocument", backref=db.backref("scholarship_scheme", uselist=False, cascade="all, delete-orphan"))

    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    def to_dict(self, tz: str = "Asia/Kolkata") -> dict:
        """Serialize scholarship scheme into dictionary."""
        summary = self.eligibility_criteria or self.description or ""
        elig_summary = (summary[:220] + "...") if len(summary) > 220 else summary

        return {
            "id": self.id,
            "scheme_name": self.scheme_name,
            "title": self.scheme_name,
            "department": self.department,
            "ministry": self.department,
            "jurisdiction": self.jurisdiction,
            "category": self.category,
            "document_type": "SCHEME",
            "type": "scheme",
            "description": self.description,
            "eligibility_criteria": self.eligibility_criteria,
            "eligibility_summary": elig_summary,
            "summary": elig_summary,
            "income_limit": self.income_limit,
            "caste_category": self.caste_category,
            "course_criteria": self.course_criteria,
            "benefit_details": self.benefit_details,
            "required_documents": self.required_documents,
            "application_start_date": self.application_start_date.isoformat() if self.application_start_date else None,
            "application_end_date": self.application_end_date.isoformat() if self.application_end_date else None,
            "academic_year": self.academic_year,
            "application_status": self.application_status,
            "official_scheme_url": self.official_scheme_url,
            "official_guidelines_url": self.official_guidelines_url,
            "official_url": self.official_scheme_url or "https://mahadbt2.maharashtra.gov.in/",
            "source_name": self.source_name,
            "last_verified_at": format_datetime_local(self.last_verified_at, tz_name=tz),
            "verification_status": self.verification_status,
            "is_verified": self.verification_status,
            "is_scholarship": True,
            "policy_document_id": self.policy_document_id,
        }
