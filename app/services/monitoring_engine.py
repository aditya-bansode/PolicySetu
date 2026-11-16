"""
PolicySetu — Automated Policy Monitoring & Ingestion Engine
============================================================
Executes the comprehensive 12-step end-to-end policy lifecycle:
1. Monitoring worker checks a configured government source.
2. New policy document is detected from listings.
3. Document is safely downloaded where permitted (deduplicated local storage).
4. PDF or HTML text, headings, and tables are extracted (PyMuPDF / BeautifulSoup).
5. Duplicate detection is performed using canonical URL.
6. Document metadata is saved in SQLite.
7. AI processes the document with safety guardrails.
8. Category (12 canonical categories) and stakeholder groups (8 canonical groups) are identified.
9. Plain-language summaries are generated in English, Marathi, and Hindi.
10. Policy is published on the dashboard with verified status.
11. If an existing document changes, create a new version with meaningful diff checking.
12. Record clause-level differences and plain-language explanation for version comparison.

Reliability & Error Handling:
- If AI is unavailable or degraded, still save the document and set processing_status.
- If one source fails, other sources continue monitoring without disruption.
- If a document cannot be extracted (corrupted, password-protected), record error status without discarding.
- Store publication dates separately from detection timestamps (never invent dates).
"""

import os
import time
import json
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.extensions import db
from app.models.source import GovernmentSource
from app.models.document import PolicyDocument, DocumentVersion, PolicyChange
from app.models.analysis import PolicyAnalysis
from app.models.monitoring import MonitoringLog
from app.adapters.registry import get_adapter, get_all_registered_adapters
from app.storage.document_storage import DocumentStorageManager
from app.extractors.document_extractor import DocumentExtractor
from app.services.comparison_engine import PolicyComparisonEngine
from app.ai.classifier import policy_classifier
from app.ai.summarizer import policy_summarizer
from app.ai.extractor import PolicyExtractor
from app.ai.explainer import PolicyExplainer
from app.utils.helpers import hash_content, utc_now

logger = logging.getLogger("policysetu.monitoring_engine")


class PolicyMonitoringEngine:
    """
    Core monitoring coordinator executing scheduled and on-demand crawlers,
    document extraction, version comparisons, and AI processing.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage = DocumentStorageManager(base_dir=storage_dir or os.path.join("data", "documents"))

    def scan_source(self, source_id: int, max_items: int = 15) -> Dict[str, Any]:
        """
        Execute full end-to-end detection and ingestion pipeline on a single GovernmentSource.
        """
        source = db.session.get(GovernmentSource, source_id)
        if not source:
            return {"success": False, "error": f"Source {source_id} not found."}

        adapter = get_adapter(source.name)
        start_time = time.time()
        checked_at = utc_now()

        # Handle unconfigured or inaccessible sources
        if not adapter:
            elapsed = time.time() - start_time
            err_msg = f"No verified source adapter implemented for '{source.name}'."
            source.last_checked_at = checked_at
            source.last_error = err_msg
            log = MonitoringLog(
                source_id=source.id,
                checked_at=checked_at,
                status="warning",
                documents_found=0,
                error_message=err_msg,
                execution_time=round(elapsed, 2)
            )
            db.session.add(log)
            db.session.commit()
            return {"success": False, "source": source.name, "status": "warning", "message": err_msg}

        health = adapter.check_health()
        if not health.get("is_healthy", False) or not source.enabled:
            elapsed = time.time() - start_time
            msg = health.get("message", "Source marked inactive or inaccessible.")
            source.last_checked_at = checked_at
            source.last_error = msg
            log = MonitoringLog(
                source_id=source.id,
                checked_at=checked_at,
                status="warning",
                documents_found=0,
                error_message=msg,
                execution_time=round(elapsed, 2)
            )
            db.session.add(log)
            db.session.commit()
            return {"success": True, "source": source.name, "status": "warning", "message": msg}

        new_count = 0
        modified_count = 0
        unchanged_count = 0
        errors: List[str] = []

        try:
            # Step 1: Retrieve document listings
            raw_listings = adapter.fetch_recent_documents(limit=max_items)
            total_found = len(raw_listings)

            for raw in raw_listings:
                try:
                    # Step 2: Extract & normalize canonical URL
                    raw_url = raw.get("url") or raw.get("canonical_url") or raw.get("pdf_url") or ""
                    canonical_url = adapter.normalize_canonical_url(raw_url)
                    if not canonical_url:
                        continue

                    # Step 5: Duplicate detection using canonical_url
                    existing = PolicyDocument.query.filter_by(canonical_url=canonical_url).first()

                    # Parse initial metadata from adapter
                    parsed = adapter.parse_document(raw)
                    if not parsed:
                        continue

                    title = parsed.get("title") or "Government Policy Document"
                    department = parsed.get("department") or source.department or "Government Portal"
                    jurisdiction = parsed.get("jurisdiction") or source.jurisdiction or "Central Government"
                    state = parsed.get("state") or source.state
                    doc_type = parsed.get("document_type", "policy")
                    pub_date = parsed.get("publication_date")

                    # Step 3 & 4: Download where permitted and extract text
                    extracted_text = parsed.get("content", "")
                    saved_file_path = parsed.get("original_file_path")
                    processing_status = "completed"

                    # If there's an explicit file or PDF URL, download & extract using DocumentExtractor
                    pdf_or_doc_url = raw.get("pdf_url") or (raw_url if raw_url.lower().endswith(".pdf") else None)
                    if pdf_or_doc_url:
                        try:
                            resp = adapter.safe_get(pdf_or_doc_url, timeout=adapter.timeout)
                            if resp.status_code == 200 and resp.content:
                                storage_res = self.storage.save_document(
                                    content_bytes=resp.content,
                                    filename_hint=os.path.basename(pdf_or_doc_url) or "policy.pdf",
                                    source_id=source.id
                                )
                                saved_file_path = storage_res["file_path"]

                                # Run extraction
                                ext_res = DocumentExtractor.extract_from_pdf(resp.content)
                                if ext_res.get("text"):
                                    extracted_text = ext_res["text"]
                                if ext_res.get("ocr_required"):
                                    processing_status = "ocr_required"
                        except Exception as dl_err:
                            logger.warning(f"[{source.name}] File download/extraction error: {dl_err}")
                            processing_status = "extraction_degraded"
                            if not extracted_text:
                                extracted_text = f"Official document link: {pdf_or_doc_url}. Title: {title}"

                    if not extracted_text:
                        extracted_text = f"{title}. Issued by {department}. Jurisdiction: {jurisdiction}."

                    # Compute SHA-256 content hash
                    content_hash = hash_content(extracted_text)

                    # ─── CASE A: NEW POLICY DOCUMENT DETECTED ─────────────────────
                    if not existing:
                        # Step 7, 8, 9: AI Processing (Classification, Extraction, Summaries)
                        ai_category = "General"
                        intelligence: Dict[str, Any] = {}
                        summaries: Dict[str, str] = {}

                        try:
                            # Step 8: Classify into 12 canonical categories
                            cat_res = policy_classifier.classify(title=title, text=extracted_text, department=department)
                            ai_category = cat_res.get("category", "General")

                            # Step 8: Identify stakeholder groups, provisions, dates, conditions
                            intelligence = PolicyExtractor.extract_all(title=title, text=extracted_text, department=department)

                            # Step 9: Generate plain-language summaries in EN, HI, MR
                            summaries = policy_summarizer.summarize_multilingual(
                                title=title,
                                text=extracted_text,
                                department=department
                            )
                        except Exception as ai_err:
                            logger.warning(f"[{source.name}] AI intelligence processing error for '{title[:40]}': {ai_err}")
                            processing_status = "ai_degraded"
                            # Fallback summaries and extractions
                            summaries = {
                                "en": f"Official policy document: {title}. Issued by {department}.",
                                "hi": f"आधिकारिक नीति दस्तावेज: {title}. विभाग: {department}.",
                                "mr": f"अधिकृत शासन निर्णय/धोरण: {title}. विभाग: {department}.",
                            }
                            intelligence = {
                                "key_provisions": [f"Government notification on {title}."],
                                "important_dates": {"detected_date": checked_at.strftime("%Y-%m-%d")},
                                "conditions": "Refer to official source guidelines.",
                                "affected_groups": {"Citizens": "General beneficiaries covered under department jurisdiction."},
                                "confidence_score": 0.80,
                            }

                        # Step 6: Save Document Metadata
                        doc = PolicyDocument(
                            source_id=source.id,
                            title=title,
                            canonical_url=canonical_url,
                            department=department,
                            jurisdiction=jurisdiction,
                            state=state,
                            document_type=doc_type,
                            category=ai_category,
                            publication_date=pub_date,
                            detected_at=checked_at,
                            content=extracted_text,
                            content_hash=content_hash,
                            original_file_path=saved_file_path,
                            language=parsed.get("language", "en"),
                            ai_summary=summaries.get("en", title),
                            processing_status=processing_status
                        )
                        db.session.add(doc)
                        db.session.flush()

                        # Step 9: Store Document Version 1
                        v1 = DocumentVersion(
                            document_id=doc.id,
                            version_number=1,
                            content=extracted_text,
                            content_hash=content_hash,
                            captured_at=checked_at
                        )
                        db.session.add(v1)

                        # Step 9: Store PolicyAnalysis (Multilingual summaries & structured extraction)
                        analysis = PolicyAnalysis(
                            document_id=doc.id,
                            summary_en=summaries.get("en", title),
                            summary_hi=summaries.get("hi", title),
                            summary_mr=summaries.get("mr", title),
                            key_provisions=json.dumps(intelligence.get("key_provisions", []), ensure_ascii=False),
                            important_dates=json.dumps(intelligence.get("important_dates", {}), ensure_ascii=False),
                            conditions=intelligence.get("conditions", "Standard scheme guidelines apply."),
                            affected_groups=json.dumps(intelligence.get("affected_groups", {}), ensure_ascii=False),
                            confidence_score=intelligence.get("confidence_score", 0.95),
                            created_at=checked_at
                        )
                        db.session.add(analysis)

                        # Step 10: Commit transaction -> Published on Dashboard!
                        db.session.commit()
                        new_count += 1
                        logger.info(f"[{source.name}] Ingested new policy '{doc.title[:45]}' (v1, Cat: {ai_category})")

                    # ─── CASE B: EXISTING DOCUMENT MODIFICATION CHECK ─────────────
                    else:
                        # Step 11: Check for content hash change
                        if existing.content_hash != content_hash:
                            # Verify meaningful difference using PolicyComparisonEngine
                            has_diff = PolicyComparisonEngine.has_meaningful_difference(
                                old_text=existing.content or "",
                                new_text=extracted_text
                            )

                            if has_diff:
                                last_ver = (
                                    DocumentVersion.query.filter_by(document_id=existing.id)
                                    .order_by(DocumentVersion.version_number.desc())
                                    .first()
                                )
                                new_vnum = (last_ver.version_number + 1) if last_ver else 2

                                # Create new version record
                                new_ver = DocumentVersion(
                                    document_id=existing.id,
                                    version_number=new_vnum,
                                    content=extracted_text,
                                    content_hash=content_hash,
                                    captured_at=checked_at
                                )
                                db.session.add(new_ver)
                                db.session.flush()

                                # Step 12: Run comparison and explain changes
                                comp = PolicyComparisonEngine.compare(
                                    old_text=existing.content or "",
                                    new_text=extracted_text,
                                    v1_num=last_ver.version_number if last_ver else 1,
                                    v2_num=new_vnum
                                )

                                # AI change narrative
                                explanation = PolicyExplainer.explain_changes(
                                    title=existing.title,
                                    old_text=existing.content or "",
                                    new_text=extracted_text,
                                    diff_summary=comp.get("diff_summary"),
                                    language="en"
                                )

                                # Record PolicyChange
                                change = PolicyChange(
                                    document_id=existing.id,
                                    old_version_id=last_ver.id if last_ver else None,
                                    new_version_id=new_ver.id,
                                    change_type="modified",
                                    change_description=f"Promoted to version {new_vnum}. " + explanation.get("summary_explanation", f"Policy updated to version {new_vnum}."),
                                    evidence=json.dumps({
                                        "diff_summary": comp.get("diff_summary"),
                                        "changed_sections": comp.get("changed_sections", [])
                                    }, ensure_ascii=False),
                                    created_at=checked_at
                                )
                                db.session.add(change)

                                # Update parent document and analysis
                                existing.content = extracted_text
                                existing.content_hash = content_hash
                                existing.updated_at = checked_at
                                if saved_file_path:
                                    existing.original_file_path = saved_file_path

                                # Re-run summaries for updated document
                                try:
                                    updated_summaries = policy_summarizer.summarize_multilingual(
                                        title=existing.title,
                                        text=extracted_text,
                                        department=existing.department
                                    )
                                    existing.ai_summary = updated_summaries.get("en", existing.ai_summary)

                                    if existing.analysis:
                                        existing.analysis.summary_en = updated_summaries.get("en", existing.analysis.summary_en)
                                        existing.analysis.summary_hi = updated_summaries.get("hi", existing.analysis.summary_hi)
                                        existing.analysis.summary_mr = updated_summaries.get("mr", existing.analysis.summary_mr)
                                except Exception as e_sum:
                                    logger.warning(f"Could not re-summarize modified policy: {e_sum}")

                                db.session.commit()
                                modified_count += 1
                                logger.info(f"[{source.name}] Modified policy '{existing.title[:45]}' promoted to v{new_vnum}")
                            else:
                                unchanged_count += 1
                        else:
                            unchanged_count += 1

                except Exception as doc_err:
                    db.session.rollback()
                    logger.warning(f"[{source.name}] Error ingesting individual document: {doc_err}")
                    errors.append(str(doc_err))

            # Step 10: Record monitoring logs and update source health
            elapsed = time.time() - start_time
            source.last_checked_at = checked_at
            source.last_success_at = checked_at
            source.last_error = "; ".join(errors[:2]) if errors else None

            log = MonitoringLog(
                source_id=source.id,
                checked_at=checked_at,
                status="success" if not errors else "warning",
                documents_found=total_found,
                error_message="; ".join(errors[:3]) if errors else None,
                execution_time=round(elapsed, 2)
            )
            db.session.add(log)
            db.session.commit()

            return {
                "success": True,
                "source": source.name,
                "status": "success",
                "documents_found": total_found,
                "new_documents": new_count,
                "modified_documents": modified_count,
                "unchanged_documents": unchanged_count,
                "execution_time_seconds": round(elapsed, 2)
            }

        except Exception as e:
            db.session.rollback()
            elapsed = time.time() - start_time
            err_msg = f"Crawl failed: {type(e).__name__}: {str(e)}"
            logger.error(f"[{source.name}] {err_msg}")

            source.last_checked_at = checked_at
            source.last_error = err_msg

            log = MonitoringLog(
                source_id=source.id,
                checked_at=checked_at,
                status="failed",
                documents_found=0,
                error_message=err_msg,
                execution_time=round(elapsed, 2)
            )
            db.session.add(log)
            db.session.commit()

            return {
                "success": False,
                "source": source.name,
                "status": "failed",
                "error": err_msg,
                "execution_time_seconds": round(elapsed, 2)
            }

    def scan_all_sources(self, max_items_per_source: int = 15) -> Dict[str, Any]:
        """
        Execute automated scan across all registered government sources.
        Continues monitoring other sources even if one fails.
        """
        sources = GovernmentSource.query.all()
        results = []
        total_new = 0
        total_modified = 0
        total_found = 0

        logger.info(f"Starting policy monitoring cycle across {len(sources)} sources.")

        for source in sources:
            res = self.scan_source(source.id, max_items=max_items_per_source)
            results.append(res)
            if res.get("success"):
                total_new += res.get("new_documents", 0)
                total_modified += res.get("modified_documents", 0)
                total_found += res.get("documents_found", 0)

        summary = {
            "timestamp": utc_now().isoformat(),
            "sources_scanned": len(sources),
            "total_documents_found": total_found,
            "new_documents_detected": total_new,
            "modified_documents_detected": total_modified,
            "details": results
        }
        logger.info(f"Monitoring cycle complete: {total_new} new, {total_modified} modified.")
        return summary
