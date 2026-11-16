"""
PolicySetu — Integrated Document Processing Service
===================================================
Coordinates deduplicated local document storage, PyMuPDF / HTML extraction,
meaningful difference checking, versioning, and change tracking.
"""

import os
import logging
from typing import Dict, Any, Optional, Union

from app.extensions import db
from app.models.document import PolicyDocument, DocumentVersion, PolicyChange
from app.storage.document_storage import DocumentStorageManager
from app.extractors.document_extractor import DocumentExtractor
from app.services.comparison_engine import PolicyComparisonEngine
from app.utils.helpers import hash_content, utc_now

logger = logging.getLogger("policysetu.document_processing")


class DocumentProcessingService:
    """
    High-level document processing service integrating storage, extraction,
    and version comparison.
    """

    def __init__(self, storage_manager: Optional[DocumentStorageManager] = None):
        self.storage = storage_manager or DocumentStorageManager()

    def process_document(
        self,
        content_bytes: bytes,
        filename_hint: str,
        canonical_url: str,
        title: Optional[str] = None,
        department: Optional[str] = None,
        source_id: Optional[int] = None,
        jurisdiction: str = "Central Government",
        state: Optional[str] = None,
        document_type: str = "policy",
        category: str = "General",
        publication_date: Optional[Any] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Process incoming document bytes (PDF or HTML):
        1. Store deduplicated file in organized local directory.
        2. Extract full text, metadata, headings, and tables.
        3. Detect OCR requirement for scanned documents.
        4. Detect new vs modified version with meaningful difference checking.
        5. Persist document, version, and policy change records in SQLite.
        """
        # 1. Deduplicated Storage
        storage_res = self.storage.save_document(
            content_bytes=content_bytes,
            filename_hint=filename_hint,
            source_id=source_id,
        )
        file_path = storage_res["file_path"]
        content_hash = storage_res["content_hash"]
        is_pdf = file_path.lower().endswith(".pdf") or content_bytes.startswith(b"%PDF")

        # 2. Extract Document Content
        if is_pdf:
            extracted = DocumentExtractor.extract_from_pdf(content_bytes)
        else:
            html_str = content_bytes.decode("utf-8", errors="replace")
            extracted = DocumentExtractor.extract_from_html(html_str, base_url=canonical_url)

        extracted_text = extracted.get("text", "")
        # If text is empty (e.g. scanned PDF), fallback to title or minimal descriptor
        if not extracted_text:
            extracted_text = title or filename_hint

        final_title = title or extracted.get("metadata", {}).get("title") or filename_hint
        ocr_required = extracted.get("ocr_required", False)
        ocr_status = extracted.get("ocr_status", "not_required")

        # 3. Check for existing document in database
        existing = PolicyDocument.query.filter_by(canonical_url=canonical_url).first()

        if not existing:
            # Step 4a: Newly published document (Version 1)
            doc = PolicyDocument(
                source_id=source_id,
                title=final_title,
                canonical_url=canonical_url,
                department=department or "Official Portal",
                jurisdiction=jurisdiction,
                state=state,
                document_type=document_type,
                category=category,
                publication_date=publication_date,
                detected_at=utc_now(),
                content=extracted_text,
                content_hash=content_hash,
                original_file_path=file_path,
                language=language,
                processing_status="completed",
            )
            db.session.add(doc)
            db.session.flush()

            v1 = DocumentVersion(
                document_id=doc.id,
                version_number=1,
                content=extracted_text,
                content_hash=content_hash,
                captured_at=utc_now(),
            )
            db.session.add(v1)
            db.session.commit()

            logger.info(f"[Processing] Ingested new document '{doc.title[:40]}' (v1, {storage_res['file_size']} bytes).")

            return {
                "success": True,
                "action": "created",
                "document_id": doc.id,
                "version_number": 1,
                "file_path": file_path,
                "content_hash": content_hash,
                "is_duplicate_file": storage_res["is_duplicate"],
                "ocr_required": ocr_required,
                "ocr_status": ocr_status,
                "page_count": extracted.get("page_count", 1),
                "headings_count": len(extracted.get("headings", [])),
                "tables_count": len(extracted.get("tables", [])),
            }

        else:
            # Step 4b: Existing document URL — verify meaningful content difference
            has_diff = PolicyComparisonEngine.has_meaningful_difference(
                old_text=existing.content or "",
                new_text=extracted_text
            )

            if not has_diff:
                logger.info(f"[Processing] Content identical for '{existing.title[:40]}'. Skipping redundant version.")
                return {
                    "success": True,
                    "action": "unchanged",
                    "document_id": existing.id,
                    "version_number": existing.versions.count(),
                    "file_path": file_path,
                    "content_hash": content_hash,
                    "is_duplicate_file": storage_res["is_duplicate"],
                    "ocr_required": ocr_required,
                }

            # Meaningful change confirmed! Create next version and record diff
            last_ver = (
                DocumentVersion.query.filter_by(document_id=existing.id)
                .order_by(DocumentVersion.version_number.desc())
                .first()
            )
            new_vnum = (last_ver.version_number + 1) if last_ver else 2

            new_ver = DocumentVersion(
                document_id=existing.id,
                version_number=new_vnum,
                content=extracted_text,
                content_hash=content_hash,
                captured_at=utc_now(),
            )
            db.session.add(new_ver)
            db.session.flush()

            # Run clause-level comparison
            comp = PolicyComparisonEngine.compare(
                old_text=existing.content or "",
                new_text=extracted_text,
                v1_num=last_ver.version_number if last_ver else 1,
                v2_num=new_vnum,
            )

            # Record PolicyChange
            change = PolicyChange(
                document_id=existing.id,
                old_version_id=last_ver.id if last_ver else None,
                new_version_id=new_ver.id,
                change_type="modified",
                change_description=comp["diff_summary"],
                evidence=comp["unified_diff"][:4000],
                created_at=utc_now(),
            )
            db.session.add(change)

            # Update existing document
            existing.content = extracted_text
            existing.content_hash = content_hash
            existing.original_file_path = file_path
            existing.updated_at = utc_now()
            db.session.commit()

            logger.info(f"[Processing] Document updated to v{new_vnum} for '{existing.title[:40]}'.")

            return {
                "success": True,
                "action": "modified",
                "document_id": existing.id,
                "version_number": new_vnum,
                "file_path": file_path,
                "content_hash": content_hash,
                "is_duplicate_file": storage_res["is_duplicate"],
                "ocr_required": ocr_required,
                "comparison": comp,
            }
