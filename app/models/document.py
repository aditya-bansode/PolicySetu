"""
PolicySetu — PolicyDocument, DocumentVersion, PolicyChange Models
================================================================
Handles document lifecycle, cryptographic hashing, versioning, and change tracking.
"""

import re
from app.extensions import db
from app.utils.helpers import utc_now, format_datetime_local, hash_content

# ── Supported Document Types (12 Canonical Categories) ─────────────────────────
DOC_TYPE_POLICY = "POLICY"
DOC_TYPE_NOTIFICATION = "NOTIFICATION"
DOC_TYPE_GOVERNMENT_RESOLUTION = "GOVERNMENT_RESOLUTION"
DOC_TYPE_ACT = "ACT"
DOC_TYPE_AMENDMENT = "AMENDMENT"
DOC_TYPE_CIRCULAR = "CIRCULAR"
DOC_TYPE_GUIDELINE = "GUIDELINE"
DOC_TYPE_SCHEME = "SCHEME"
DOC_TYPE_ORDER = "ORDER"
DOC_TYPE_PRESS_RELEASE = "PRESS_RELEASE"
DOC_TYPE_NEWS = "NEWS"
DOC_TYPE_OTHER = "OTHER"

VALID_POLICY_DOCUMENT_TYPES = [
    DOC_TYPE_POLICY,
    DOC_TYPE_NOTIFICATION,
    DOC_TYPE_GOVERNMENT_RESOLUTION,
    DOC_TYPE_ACT,
    DOC_TYPE_AMENDMENT,
    DOC_TYPE_CIRCULAR,
    DOC_TYPE_GUIDELINE,
    DOC_TYPE_SCHEME,
    DOC_TYPE_ORDER,
]

EXCLUDED_DOCUMENT_TYPES = [
    DOC_TYPE_PRESS_RELEASE,
    DOC_TYPE_NEWS,
    DOC_TYPE_OTHER,
]

ALL_DOCUMENT_TYPES = VALID_POLICY_DOCUMENT_TYPES + EXCLUDED_DOCUMENT_TYPES


def normalize_document_type(raw_type: str) -> str:
    """Normalize arbitrary document type strings into the 12 canonical types."""
    if not raw_type:
        return DOC_TYPE_POLICY
    cleaned = re.sub(r"[_\s\-]+", "_", raw_type.strip()).upper()

    mapping = {
        "POLICY": DOC_TYPE_POLICY,
        "NOTIFICATION": DOC_TYPE_NOTIFICATION,
        "GOVERNMENT_RESOLUTION": DOC_TYPE_GOVERNMENT_RESOLUTION,
        "GOVT_RESOLUTION": DOC_TYPE_GOVERNMENT_RESOLUTION,
        "RESOLUTION": DOC_TYPE_GOVERNMENT_RESOLUTION,
        "GR": DOC_TYPE_GOVERNMENT_RESOLUTION,
        "ACT": DOC_TYPE_ACT,
        "AMENDMENT": DOC_TYPE_AMENDMENT,
        "CIRCULAR": DOC_TYPE_CIRCULAR,
        "GUIDELINE": DOC_TYPE_GUIDELINE,
        "GUIDELINES": DOC_TYPE_GUIDELINE,
        "SCHEME": DOC_TYPE_SCHEME,
        "ORDER": DOC_TYPE_ORDER,
        "PRESS_RELEASE": DOC_TYPE_PRESS_RELEASE,
        "PRESS": DOC_TYPE_PRESS_RELEASE,
        "PIB": DOC_TYPE_PRESS_RELEASE,
        "NEWS": DOC_TYPE_NEWS,
        "ARTICLE": DOC_TYPE_NEWS,
    }
    return mapping.get(cleaned, DOC_TYPE_OTHER)


def is_placeholder_or_fake_url(url: str) -> bool:
    """Check if a URL is a constructed placeholder or fake government URL."""
    if not url or not isinstance(url, str):
        return True
    u = url.strip().lower()
    if u in ("", "#", "none", "null", "about:blank"):
        return True
    # Detect fabricated PRIDs like PRID=0000001 or PRID=0000002
    if re.search(r"prid=0{4,}\d+", u):
        return True
    # Detect placeholder filenames like 00001.pdf or dummy paths
    if re.search(r"/0{4,}\d+\.pdf", u):
        return True
    if "policysetu.gov.in" in u:
        return True
    return False


class PolicyDocument(db.Model):
    __tablename__ = "policy_documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, db.ForeignKey("government_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    canonical_url = db.Column(db.String(1024), nullable=False, unique=True, index=True)
    official_url = db.Column(db.String(1024), nullable=True)  # Direct official document URL
    source_listing_url = db.Column(db.String(1024), nullable=True)  # Official portal / listing URL
    department = db.Column(db.String(255), nullable=True)
    jurisdiction = db.Column(db.String(100), nullable=False, default="Central Government", index=True)
    state = db.Column(db.String(100), nullable=True, index=True)
    document_type = db.Column(db.String(50), nullable=False, default=DOC_TYPE_POLICY, index=True)
    category = db.Column(db.String(100), nullable=True, index=True)
    publication_date = db.Column(db.Date, nullable=True, index=True)
    detected_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    first_detected_at = db.Column(db.DateTime, nullable=True, default=utc_now, index=True)
    content = db.Column(db.Text, nullable=True)
    content_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA-256
    original_file_path = db.Column(db.String(1024), nullable=True)
    language = db.Column(db.String(10), nullable=False, default="en")
    ai_summary = db.Column(db.Text, nullable=True)
    current_version = db.Column(db.Integer, nullable=False, default=1)
    is_verified = db.Column(db.Boolean, nullable=False, default=True)
    classification_status = db.Column(db.String(50), nullable=False, default="verified_policy", index=True)  # verified_policy, excluded_news, unverified
    processing_status = db.Column(db.String(50), nullable=False, default="completed", index=True)  # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    source = db.relationship("GovernmentSource", back_populates="documents")
    versions = db.relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_number.desc()", lazy="dynamic")
    changes = db.relationship("PolicyChange", back_populates="document", cascade="all, delete-orphan", order_by="PolicyChange.created_at.desc()", lazy="dynamic")
    analysis = db.relationship("PolicyAnalysis", back_populates="document", uselist=False, cascade="all, delete-orphan")

    @property
    def last_updated_at(self):
        return self.updated_at

    def to_dict(self, tz: str = "Asia/Kolkata", include_content: bool = False, lang: str = "en") -> dict:
        summary = self.ai_summary
        title = self.title

        # Localize title and summary if analysis exists
        if self.analysis:
            if lang == "hi":
                summary = self.analysis.summary_hi or self.ai_summary
            elif lang == "mr":
                summary = self.analysis.summary_mr or self.ai_summary
            else:
                summary = self.analysis.summary_en or self.ai_summary

        detection_date = self.first_detected_at or self.detected_at or self.created_at
        is_new_doc = True if (utc_now() - detection_date).days <= 14 else False
        v_count = self.versions.count() if hasattr(self, "versions") else self.current_version
        ch_count = self.changes.count() if hasattr(self, "changes") else 0
        is_mod_doc = v_count > 1 or ch_count > 0 or self.current_version > 1

        # Check official URL validity — avoid returning fake/placeholder links
        raw_official = self.official_url or self.canonical_url
        if is_placeholder_or_fake_url(raw_official):
            resolved_official_url = None
            official_url_available = False
        else:
            resolved_official_url = raw_official
            official_url_available = True

        listing_url = self.source_listing_url or (self.source.base_url if self.source else None)
        norm_type = normalize_document_type(self.document_type)

        data = {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source.name if self.source else None,
            "source_base_url": self.source.base_url if self.source else None,
            "title": title,
            "title_hi": title,
            "title_mr": title,
            "canonical_url": self.canonical_url,
            "official_url": resolved_official_url,
            "official_url_available": official_url_available,
            "source_listing_url": listing_url,
            "department": self.department,
            "ministry": self.department,
            "jurisdiction": self.jurisdiction,
            "state": self.state,
            "document_type": norm_type,
            "type": norm_type.lower(),
            "category": self.category,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "published_date": self.publication_date.isoformat() if self.publication_date else None,
            "detected_at": format_datetime_local(self.detected_at, tz_name=tz),
            "first_detected_at": format_datetime_local(detection_date, tz_name=tz),
            "detected_date": format_datetime_local(detection_date, tz_name=tz, fmt="%Y-%m-%d"),
            "content_hash": self.content_hash,
            "original_file_path": self.original_file_path,
            "language": self.language,
            "summary": summary,
            "ai_summary": summary,
            "summary_hi": self.analysis.summary_hi if self.analysis else self.ai_summary,
            "summary_mr": self.analysis.summary_mr if self.analysis else self.ai_summary,
            "key_points": self.analysis.get_key_provisions_list() if self.analysis else [],
            "affected_groups": self.analysis.get_affected_groups_dict() if self.analysis else {},
            "stakeholders": list(self.analysis.get_affected_groups_dict().keys()) if self.analysis and self.analysis.get_affected_groups_dict() else ["Citizens"],
            "impact_areas": [self.category] if self.category else ["Governance"],
            "is_new": is_new_doc,
            "is_modified": is_mod_doc,
            "current_version": max(self.current_version, v_count),
            "is_verified": self.is_verified,
            "classification_status": self.classification_status,
            "is_news": norm_type in EXCLUDED_DOCUMENT_TYPES or self.classification_status == "excluded_news",
            "processing_status": self.processing_status,
            "created_at": format_datetime_local(self.created_at, tz_name=tz),
            "updated_at": format_datetime_local(self.updated_at, tz_name=tz),
            "last_updated_at": format_datetime_local(self.updated_at, tz_name=tz),
        }
        if hasattr(self, "scholarship_scheme") and self.scholarship_scheme:
            sch = self.scholarship_scheme
            data["is_scholarship"] = True
            data["scheme_name"] = sch.scheme_name
            data["academic_year"] = sch.academic_year
            data["application_status"] = sch.application_status
            data["eligibility_criteria"] = sch.eligibility_criteria
            data["income_limit"] = sch.income_limit
            data["caste_category"] = sch.caste_category
            data["course_criteria"] = sch.course_criteria
            data["benefit_details"] = sch.benefit_details
            data["required_documents"] = sch.required_documents
            data["official_scheme_url"] = sch.official_scheme_url
            data["official_guidelines_url"] = sch.official_guidelines_url
            data["last_verified_at"] = format_datetime_local(sch.last_verified_at, tz_name=tz)
            data["verification_status"] = sch.verification_status
            if sch.eligibility_criteria and (not summary or summary == self.title):
                data["summary"] = (sch.eligibility_criteria[:220] + "...") if len(sch.eligibility_criteria) > 220 else sch.eligibility_criteria
        if include_content:
            data["content"] = self.content
        return data


class DocumentVersion(db.Model):
    __tablename__ = "document_versions"
    __table_args__ = (
        db.UniqueConstraint("document_id", "version_number", name="uq_document_version"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_id = db.Column(db.Integer, db.ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    content = db.Column(db.Text, nullable=True)
    content_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA-256
    captured_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    document = db.relationship("PolicyDocument", back_populates="versions")

    def to_dict(self, tz: str = "Asia/Kolkata", include_content: bool = True) -> dict:
        data = {
            "id": self.id,
            "document_id": self.document_id,
            "version_number": self.version_number,
            "content_hash": self.content_hash,
            "captured_at": format_datetime_local(self.captured_at, tz_name=tz),
        }
        if include_content:
            data["content"] = self.content
        return data


class PolicyChange(db.Model):
    __tablename__ = "policy_changes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_id = db.Column(db.Integer, db.ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    old_version_id = db.Column(db.Integer, db.ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    new_version_id = db.Column(db.Integer, db.ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    change_type = db.Column(db.String(50), nullable=False, default="modified")  # modified, added, amendment, superseded
    change_description = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, nullable=True)  # JSON or text diff evidence
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    document = db.relationship("PolicyDocument", back_populates="changes")
    old_version = db.relationship("DocumentVersion", foreign_keys=[old_version_id])
    new_version = db.relationship("DocumentVersion", foreign_keys=[new_version_id])

    def to_dict(self, tz: str = "Asia/Kolkata") -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "old_version_id": self.old_version_id,
            "new_version_id": self.new_version_id,
            "change_type": self.change_type,
            "change_description": self.change_description,
            "evidence": self.evidence,
            "created_at": format_datetime_local(self.created_at, tz_name=tz),
        }
