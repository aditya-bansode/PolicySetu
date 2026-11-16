"""
PolicySetu — Database Seeder
============================
Seeds SQLite database with initial verified government sources, policy documents,
multilingual analyses, versions, change records, categories, and monitoring logs.
"""

from datetime import datetime, date
from app.extensions import db
from app.models import (
    GovernmentSource,
    PolicyDocument,
    DocumentVersion,
    PolicyChange,
    PolicyAnalysis,
    MonitoringLog,
    PolicyCategory,
)
from app.utils.helpers import hash_content, utc_now
import json


def seed_database():
    """Seed the database if empty or missing records."""
    # 1. Categories
    categories_data = [
        ("Agriculture", "शेती", "कृषि"),
        ("Education", "शिक्षण", "शिक्षा"),
        ("Health", "आरोग्य", "स्वास्थ्य"),
        ("Finance & Banking", "वित्त", "वित्त"),
        ("Housing", "गृहनिर्माण", "आवास"),
        ("Employment", "रोजगार", "रोज़गार"),
        ("Environment", "पर्यावरण", "पर्यावरण"),
        ("Digital India", "डिजिटल भारत", "डिजिटल इंडिया"),
        ("Social Welfare", "समाज कल्याण", "समाज कल्याण"),
        ("Business & MSME", "व्यवसाय", "व्यापार"),
        ("Infrastructure", "पायाभूत सुविधा", "बुनियादी ढांचा"),
        ("Women & Child", "महिला व बाल", "महिला एवं बाल"),
        ("Senior Citizens", "ज्येष्ठ नागरिक", "वरिष्ठ नागरिक"),
        ("Youth", "युवा", "युवा"),
        ("Defence", "संरक्षण", "रक्षा"),
    ]

    for en, mr, hi in categories_data:
        if not PolicyCategory.query.filter_by(name_en=en).first():
            cat = PolicyCategory(name_en=en, name_mr=mr, name_hi=hi)
            db.session.add(cat)
    db.session.commit()

    # 2. Government Sources
    sources_data = [
        {
            "id": 1,
            "name": "Press Information Bureau",
            "base_url": "https://pib.gov.in",
            "jurisdiction": "Central Government",
            "state": None,
            "department": "Ministry of Information & Broadcasting",
            "source_type": "pib",
            "enabled": True,
            "last_checked_at": datetime(2026, 11, 15, 14, 30),
            "last_success_at": datetime(2026, 11, 15, 14, 30),
        },
        {
            "id": 2,
            "name": "India.gov.in National Portal",
            "base_url": "https://www.india.gov.in",
            "jurisdiction": "Central Government",
            "state": None,
            "department": "National Informatics Centre",
            "source_type": "portal",
            "enabled": True,
            "last_checked_at": datetime(2026, 11, 15, 13, 0),
            "last_success_at": datetime(2026, 11, 15, 13, 0),
        },
        {
            "id": 3,
            "name": "MyGov India",
            "base_url": "https://www.mygov.in",
            "jurisdiction": "Central Government",
            "state": None,
            "department": "Ministry of Electronics & IT",
            "source_type": "portal",
            "enabled": True,
            "last_checked_at": datetime(2026, 11, 15, 12, 0),
            "last_success_at": datetime(2026, 11, 15, 12, 0),
        },
        {
            "id": 4,
            "name": "Legislative Department",
            "base_url": "https://legislative.gov.in",
            "jurisdiction": "Central Government",
            "state": None,
            "department": "Ministry of Law & Justice",
            "source_type": "portal",
            "enabled": True,
            "last_checked_at": datetime(2026, 11, 15, 8, 0),
            "last_success_at": datetime(2026, 11, 15, 8, 0),
        },
        {
            "id": 5,
            "name": "e-Gazette of India",
            "base_url": "https://egazette.gov.in",
            "jurisdiction": "Central Government",
            "state": None,
            "department": "Ministry of Housing & Urban Affairs",
            "source_type": "aspnet_session",
            "enabled": False,
            "last_checked_at": datetime(2026, 11, 15, 10, 0),
            "last_success_at": None,
            "last_error": "Inaccessible via static crawler. Search requires active ASP.NET session tokens and server-side postbacks.",
        },
        {
            "id": 6,
            "name": "Maharashtra Govt. Resolutions",
            "base_url": "https://gr.maharashtra.gov.in/1145/Government-Resolutions",
            "jurisdiction": "State Government",
            "state": "Maharashtra",
            "department": "General Administration Department",
            "source_type": "html_table_pdf",
            "enabled": True,
            "last_checked_at": datetime(2026, 11, 15, 17, 18),
            "last_success_at": datetime(2026, 11, 15, 17, 18),
            "last_error": None,
        },
        {
            "id": 7,
            "name": "India Code Legislative Portal",
            "base_url": "https://indiacode.gov.in",
            "jurisdiction": "Central Government",
            "state": None,
            "department": "Ministry of Law and Justice",
            "source_type": "spa_auth",
            "enabled": False,
            "last_checked_at": datetime(2026, 11, 15, 17, 0),
            "last_success_at": None,
            "last_error": "Inaccessible via static crawler. Migrated to DSpace 7 Angular SPA; direct REST API requires Bearer authentication token.",
        },
    ]

    for s_data in sources_data:
        existing = db.session.get(GovernmentSource, s_data["id"])
        if not existing:
            src = GovernmentSource(**s_data)
            db.session.add(src)
        else:
            for k, v in s_data.items():
                setattr(existing, k, v)
    db.session.commit()


    # 3. Import Demo policies from app/demo_data.py to populate rich data
    from app.demo_data import DEMO_POLICIES, DEMO_VERSIONS, DEMO_CRAWL_LOGS
    from app.models.document import normalize_document_type, EXCLUDED_DOCUMENT_TYPES

    for p in DEMO_POLICIES:
        pub_date = None
        if p.get("published_date"):
            try:
                pub_date = datetime.strptime(p["published_date"], "%Y-%m-%d").date()
            except Exception:
                pub_date = None

        detected_dt = utc_now()
        if p.get("detected_date"):
            try:
                detected_dt = datetime.strptime(p["detected_date"], "%Y-%m-%d")
            except Exception:
                detected_dt = utc_now()

        norm_type = normalize_document_type(p.get("document_type") or p.get("type", "policy"))
        is_news = norm_type in EXCLUDED_DOCUMENT_TYPES
        class_status = p.get("classification_status") or ("excluded_news" if is_news else "verified_policy")
        official_url = p.get("official_url")
        listing_url = p.get("source_listing_url")
        canonical_url = p.get("canonical_url") or official_url or f"https://policysetu.gov.in/policy/{p['id']}"

        existing = db.session.get(PolicyDocument, p["id"])
        if not existing:
            content = f"{p['title']}\n\n{p['summary']}\n\nMinistry: {p.get('ministry')}\nDepartment: {p.get('department')}"
            c_hash = hash_content(content)

            doc = PolicyDocument(
                id=p["id"],
                source_id=p.get("source_id", 1),
                title=p["title"],
                canonical_url=canonical_url,
                official_url=official_url,
                source_listing_url=listing_url,
                department=p.get("department") or p.get("ministry"),
                jurisdiction=p.get("jurisdiction", "Central Government"),
                state="Maharashtra" if p.get("jurisdiction") == "Maharashtra" else None,
                document_type=norm_type,
                category=p.get("category", "General"),
                publication_date=pub_date,
                detected_at=detected_dt,
                first_detected_at=detected_dt,
                content=content,
                content_hash=c_hash,
                original_file_path=f"/documents/2026/{p['id']}.pdf",
                language="en",
                ai_summary=p.get("summary"),
                current_version=2 if p.get("is_modified") else 1,
                is_verified=True,
                classification_status=class_status,
                processing_status="completed"
            )
            db.session.add(doc)
            db.session.flush()

            # Add analysis
            analysis = PolicyAnalysis(
                document_id=doc.id,
                summary_en=p.get("summary"),
                summary_hi=p.get("summary_hi"),
                summary_mr=p.get("summary_mr"),
                key_provisions=json.dumps(p.get("key_points", []), ensure_ascii=False),
                important_dates=json.dumps({
                    "published": p.get("published_date"),
                    "detected": p.get("detected_date"),
                    "effective": p.get("effective_date"),
                }),
                conditions="Eligible citizens and organizations under specified guidelines.",
                affected_groups=json.dumps(p.get("affected_groups", {}), ensure_ascii=False),
                confidence_score=0.96
            )
            db.session.add(analysis)

            # Add Versions
            doc_versions = [v for v in DEMO_VERSIONS if v["policy_id"] == p["id"]]
            if doc_versions:
                for v in doc_versions:
                    v_content = f"{doc.title} (Version {v['version_number']})\n\n{v['diff_summary']}\n\n{doc.content}"
                    v_record = DocumentVersion(
                        document_id=doc.id,
                        version_number=v["version_number"],
                        content=v_content,
                        content_hash=hash_content(v_content),
                        captured_at=datetime.strptime(v["created_at"], "%Y-%m-%d") if v.get("created_at") else doc.detected_at
                    )
                    db.session.add(v_record)
                    db.session.flush()

                    if v["version_number"] > 1:
                        # Log policy change
                        ch = PolicyChange(
                            document_id=doc.id,
                            old_version_id=None,
                            new_version_id=v_record.id,
                            change_type="modified",
                            change_description=v.get("diff_summary", "Document revision detected."),
                            evidence=json.dumps(v.get("changed_sections", [])),
                            created_at=v_record.captured_at
                        )
                        db.session.add(ch)
            else:
                # Version 1 default
                v1 = DocumentVersion(
                    document_id=doc.id,
                    version_number=1,
                    content=doc.content,
                    content_hash=c_hash,
                    captured_at=doc.detected_at
                )
                db.session.add(v1)
        else:
            # Update existing record with verified URLs and classification fields
            existing.official_url = official_url
            existing.source_listing_url = listing_url
            existing.canonical_url = canonical_url
            existing.document_type = norm_type
            existing.classification_status = class_status
            existing.first_detected_at = existing.first_detected_at or existing.detected_at
            existing.is_verified = True
            v_cnt = existing.versions.count() if hasattr(existing, "versions") else 1
            existing.current_version = max(existing.current_version or 1, v_cnt, 2 if p.get("is_modified") else 1)

    db.session.commit()

    # 4. Monitoring Logs
    for cl in DEMO_CRAWL_LOGS:
        existing_log = db.session.get(MonitoringLog, cl["id"])
        if not existing_log:
            mlog = MonitoringLog(
                id=cl["id"],
                source_id=cl["source_id"],
                checked_at=datetime.fromisoformat(cl["started_at"]),
                status=cl["status"],
                documents_found=cl["policies_found"],
                error_message=cl.get("error_message"),
                execution_time=135.0
            )
            db.session.add(mlog)
    db.session.commit()
    print("Database seeding completed successfully!")
