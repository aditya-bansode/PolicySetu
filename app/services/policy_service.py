"""
PolicySetu — PolicyService
==========================
Business logic for policy document queries, filtering, versioning, change tracking, and comparisons.
"""

from datetime import datetime, date, timedelta
from sqlalchemy import or_, desc, asc
from app.extensions import db
from app.models import PolicyDocument, DocumentVersion, PolicyChange, PolicyAnalysis, GovernmentSource
from app.utils.helpers import hash_content, utc_now
from app.utils.pagination import paginate_query
import difflib
from app.services.comparison_engine import PolicyComparisonEngine




from app.models.document import (
    VALID_POLICY_DOCUMENT_TYPES,
    EXCLUDED_DOCUMENT_TYPES,
    normalize_document_type,
)


class PolicyService:
    @staticmethod
    def get_policies(filters: dict, page: int = 1, per_page: int = 10, lang: str = "en"):
        """Query policy documents with robust filtering, search, sorting, and pagination."""
        query = PolicyDocument.query.join(GovernmentSource, PolicyDocument.source_id == GovernmentSource.id, isouter=True)

        # Keyword search
        q = filters.get("q", "").strip()
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    PolicyDocument.title.ilike(search_pattern),
                    PolicyDocument.ai_summary.ilike(search_pattern),
                    PolicyDocument.department.ilike(search_pattern),
                    PolicyDocument.category.ilike(search_pattern),
                    GovernmentSource.name.ilike(search_pattern)
                )
            )

        # Category filter (supports both display names and URL slugs like 'finance-banking')
        category = filters.get("category", "").strip()
        if category:
            cat_filters = [PolicyDocument.category.ilike(f"%{category}%")]
            if "-" in category:
                cat_filters.append(PolicyDocument.category.ilike(f"%{category.replace('-', ' ')}%"))
                cat_filters.append(PolicyDocument.category.ilike(f"%{category.replace('-', '&')}%"))
                cat_filters.append(PolicyDocument.category.ilike(f"%{category.replace('-', '%')}%"))
            if "&" in category:
                cat_filters.append(PolicyDocument.category.ilike(f"%{category.replace('&', 'and')}%"))
                cat_filters.append(PolicyDocument.category.ilike(f"%{category.replace('&', '-')}%"))
            query = query.filter(or_(*cat_filters))

        # Document classification & type filter (BUG 3)
        doc_type = filters.get("type") or filters.get("document_type")
        if doc_type:
            cleaned_type = doc_type.strip().lower()
            query = query.filter(PolicyDocument.document_type.ilike(f"%{cleaned_type}%"))
        else:
            # Exclude news articles and general press releases from All Policies by default
            valid_types_lower = [t.lower() for t in VALID_POLICY_DOCUMENT_TYPES]
            query = query.filter(
                or_(
                    PolicyDocument.document_type.in_(VALID_POLICY_DOCUMENT_TYPES),
                    PolicyDocument.document_type.in_(valid_types_lower)
                ),
                PolicyDocument.classification_status != "excluded_news"
            )

        # Jurisdiction / State filter
        jurisdiction = filters.get("jurisdiction") or filters.get("state")
        if jurisdiction:
            jurisdiction = jurisdiction.strip()
            query = query.filter(
                or_(
                    PolicyDocument.jurisdiction.ilike(f"%{jurisdiction}%"),
                    PolicyDocument.state.ilike(f"%{jurisdiction}%")
                )
            )

        # Status filter (BUG 4: all, new, updated)
        status = (filters.get("status") or "").strip().lower()
        is_new_filter = status == "new" or filters.get("is_new") in (True, 1, "1", "true")
        is_modified_filter = status == "updated" or filters.get("is_modified") in (True, 1, "1", "true")

        if is_new_filter:
            # New policies: based on reliable detected_at or first_detected_at (within last 14 days)
            cutoff = utc_now() - timedelta(days=14)
            query = query.filter(
                or_(
                    PolicyDocument.first_detected_at >= cutoff,
                    PolicyDocument.detected_at >= cutoff
                )
            )
        elif is_modified_filter:
            # Updated policies: verified content change with at least two document versions or recorded change logs
            query = query.filter(
                or_(
                    PolicyDocument.current_version > 1,
                    PolicyDocument.versions.any(DocumentVersion.version_number > 1),
                    PolicyDocument.changes.any()
                )
            )

        # Sorting
        sort = filters.get("sort", "date_desc")
        if sort == "date_asc":
            query = query.order_by(asc(PolicyDocument.publication_date).nullslast(), asc(PolicyDocument.id))
        elif sort == "popular":
            query = query.order_by(desc(PolicyDocument.id))
        else:  # default date_desc
            query = query.order_by(desc(PolicyDocument.publication_date).nullslast(), desc(PolicyDocument.id))

        items, meta = paginate_query(query, page=page, per_page=per_page)
        serialized_items = [doc.to_dict(lang=lang) for doc in items]
        return serialized_items, meta

    @staticmethod
    def get_by_id(policy_id: int, lang: str = "en", include_content: bool = False):
        """Retrieve a single policy document by ID."""
        doc = db.session.get(PolicyDocument, policy_id)
        if not doc:
            return None
        res = doc.to_dict(lang=lang, include_content=include_content)
        if doc.analysis:
            res["analysis"] = doc.analysis.to_dict()
        return res

    @staticmethod
    def create_or_update_document(doc_data: dict) -> tuple[PolicyDocument, bool]:
        """
        Create a new document or add a new version if content changed.
        Guarantees duplicate prevention via canonical_url.
        Uses database transaction.
        Returns (document, is_new_version).
        """
        canonical_url = doc_data["canonical_url"].strip()
        content = doc_data.get("content", "")
        new_hash = hash_content(content)

        existing = PolicyDocument.query.filter_by(canonical_url=canonical_url).first()

        try:
            norm_type = normalize_document_type(doc_data.get("document_type", "policy"))
            is_news = norm_type in EXCLUDED_DOCUMENT_TYPES
            classification_status = doc_data.get("classification_status") or ("excluded_news" if is_news else "verified_policy")
            detected_dt = doc_data.get("detected_at", utc_now())
            first_detected = doc_data.get("first_detected_at") or detected_dt

            if not existing:
                # Create initial document
                doc = PolicyDocument(
                    source_id=doc_data.get("source_id"),
                    title=doc_data["title"],
                    canonical_url=canonical_url,
                    official_url=doc_data.get("official_url"),
                    source_listing_url=doc_data.get("source_listing_url"),
                    department=doc_data.get("department"),
                    jurisdiction=doc_data.get("jurisdiction", "Central Government"),
                    state=doc_data.get("state"),
                    document_type=norm_type,
                    category=doc_data.get("category"),
                    publication_date=doc_data.get("publication_date"),
                    detected_at=detected_dt,
                    first_detected_at=first_detected,
                    content=content,
                    content_hash=new_hash,
                    original_file_path=doc_data.get("original_file_path"),
                    language=doc_data.get("language", "en"),
                    ai_summary=doc_data.get("ai_summary"),
                    current_version=1,
                    is_verified=doc_data.get("is_verified", True),
                    classification_status=classification_status,
                    processing_status="completed"
                )
                db.session.add(doc)
                db.session.flush()

                # Add initial version 1
                v1 = DocumentVersion(
                    document_id=doc.id,
                    version_number=1,
                    content=content,
                    content_hash=new_hash,
                    captured_at=doc.detected_at
                )
                db.session.add(v1)
                db.session.commit()
                return doc, False

            else:
                # Existing document: check for content change via SHA-256
                is_changed = (existing.content_hash != new_hash)
                if is_changed:
                    # Find highest version number
                    last_ver = DocumentVersion.query.filter_by(document_id=existing.id).order_by(DocumentVersion.version_number.desc()).first()
                    new_ver_num = (last_ver.version_number + 1) if last_ver else 2

                    new_ver = DocumentVersion(
                        document_id=existing.id,
                        version_number=new_ver_num,
                        content=content,
                        content_hash=new_hash,
                        captured_at=utc_now()
                    )
                    db.session.add(new_ver)
                    existing.current_version = new_ver_num
                    db.session.flush()

                    # Record policy change
                    change = PolicyChange(
                        document_id=existing.id,
                        old_version_id=last_ver.id if last_ver else None,
                        new_version_id=new_ver.id,
                        change_type="modified",
                        change_description=doc_data.get("change_description", f"Policy document content updated to version {new_ver_num}."),
                        evidence=doc_data.get("evidence", "Content updated detected by automated monitoring."),
                        created_at=utc_now()
                    )
                    db.session.add(change)

                    # Update main document
                    existing.content = content
                    existing.content_hash = new_hash
                    existing.updated_at = utc_now()
                    if doc_data.get("ai_summary"):
                        existing.ai_summary = doc_data["ai_summary"]

                    db.session.commit()
                    return existing, True
                else:
                    # No content change, just update metadata if needed
                    existing.updated_at = utc_now()
                    db.session.commit()
                    return existing, False

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_versions(policy_id: int):
        """Retrieve all versions for a policy document."""
        versions = DocumentVersion.query.filter_by(document_id=policy_id).order_by(DocumentVersion.version_number.desc()).all()
        return [v.to_dict(include_content=False) for v in versions]

    @staticmethod
    def get_changes(policy_id: int):
        """Retrieve all change logs for a policy document."""
        changes = PolicyChange.query.filter_by(document_id=policy_id).order_by(PolicyChange.created_at.desc()).all()
        return [c.to_dict() for c in changes]

    @staticmethod
    def compare_versions(policy_id: int, v1_num: int, v2_num: int):
        """Compare two versions of a policy document and return clause-level and unified diff."""
        v1 = DocumentVersion.query.filter_by(document_id=policy_id, version_number=v1_num).first()
        v2 = DocumentVersion.query.filter_by(document_id=policy_id, version_number=v2_num).first()

        if not v1 or not v2:
            return None

        comp = PolicyComparisonEngine.compare(
            old_text=v1.content or "",
            new_text=v2.content or "",
            v1_num=v1_num,
            v2_num=v2_num,
        )

        return {
            "policy_id": policy_id,
            "v1": v1.to_dict(),
            "v2": v2.to_dict(),
            "additions": comp["additions_count"],
            "deletions": comp["deletions_count"],
            "diff": comp["unified_diff"],
            "identical": comp["identical"] or (v1.content_hash == v2.content_hash),
            "meaningful_change": comp["meaningful_change"],
            "diff_summary": comp["diff_summary"],
            "added_clauses": comp["added_clauses"],
            "removed_clauses": comp["removed_clauses"],
            "modified_clauses": comp["modified_clauses"],
            "changed_sections": comp["changed_sections"],
        }


    @staticmethod
    def get_dashboard_stats():
        """Compute live dashboard summary statistics."""
        base_eligible = PolicyDocument.query.filter(PolicyDocument.classification_status != "excluded_news")
        total_policies = base_eligible.count()
        cutoff = utc_now() - timedelta(days=14)
        new_this_week = base_eligible.filter(
            or_(
                PolicyDocument.first_detected_at >= cutoff,
                PolicyDocument.detected_at >= cutoff
            )
        ).count()
        modified_policies = base_eligible.filter(
            or_(
                PolicyDocument.current_version > 1,
                PolicyDocument.versions.any(DocumentVersion.version_number > 1),
                PolicyDocument.changes.any()
            )
        ).count()
        active_sources = GovernmentSource.query.filter_by(enabled=True).count()

        # Categories distribution
        categories = db.session.query(
            PolicyDocument.category, db.func.count(PolicyDocument.id)
        ).group_by(PolicyDocument.category).all()
        cat_stats = [{"category": c or "General", "count": count} for c, count in categories]

        # Jurisdiction distribution
        jurisdictions = db.session.query(
            PolicyDocument.jurisdiction, db.func.count(PolicyDocument.id)
        ).group_by(PolicyDocument.jurisdiction).all()
        juris_stats = [{"jurisdiction": j, "count": count} for j, count in jurisdictions]

        # Real database timeline distribution
        timeline_rows = db.session.query(
            db.func.strftime("%Y-%m", db.func.coalesce(PolicyDocument.publication_date, PolicyDocument.detected_at)).label("ym"),
            db.func.count(PolicyDocument.id)
        ).group_by("ym").order_by("ym").all()

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        timeline_stats = []
        for ym, count in (timeline_rows[-6:] if timeline_rows else []):
            if ym and "-" in ym:
                parts = ym.split("-")
                try:
                    m_idx = int(parts[1]) - 1
                    label = f"{month_names[m_idx]} {parts[0]}"
                except Exception:
                    label = ym
                timeline_stats.append({"month": label, "count": count})

        return {
            "total_policies": total_policies,
            "new_this_week": new_this_week,
            "modified_policies": modified_policies,
            "active_sources": active_sources,
            "categories": cat_stats,
            "jurisdictions": juris_stats,
            "timeline": timeline_stats,
        }
