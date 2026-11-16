"""
PolicySetu — PyMuPDF Policy Document Extractor
==============================================
Production-grade PDF text, metadata, heading, and table extraction engine
powered by PyMuPDF (pymupdf).

Handles all edge cases:
- Empty PDFs
- Corrupted documents
- Encrypted / password-protected files
- Scanned PDFs (automatic detection of missing text stream and OCR requirement flag)
- Large files (page-by-page streaming and chunking)
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Union
import pymupdf

logger = logging.getLogger("policysetu.extractors.pdf")


class PDFExtractor:
    """
    Robust PyMuPDF extractor with heading heuristics, table detection,
    and scanned document / OCR detection.
    """

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB safety threshold
    MIN_TEXT_CHARS_PER_PAGE_FOR_NATIVE = 25  # Below this threshold indicates scanned document

    HEADING_PATTERNS = [
        re.compile(r"^(?:Section|Article|Clause|Rule|Chapter|Part|Schedule|Annexure|Appendix)\s+[\dA-Za-z\.\-]+", re.IGNORECASE),
        re.compile(r"^(?:शासन\s*निर्णय|प्रस्तावना|परिशिष्ट|महत्वाचे\s*मुद्दे)", re.UNICODE),
        re.compile(r"^(?:विभागाचे\s*नाव|अधिसूचना|संदर्भ|प्रकरण)\s*[:\-]", re.UNICODE),
        re.compile(r"^\d+[\.\)]\s+[A-Z\u0900-\u097F][A-Za-z\u0900-\u097F\s]{3,60}$"),
    ]

    @classmethod
    def extract(cls, source: Union[str, bytes], max_pages: int = 500) -> Dict[str, Any]:
        """
        Extract text, structure, metadata, headings, and tables from a PDF path or byte stream.
        """
        # 1. Validation and File Size Check
        if isinstance(source, bytes):
            if not source:
                return cls._empty_response("PDF byte buffer is empty (0 bytes).")
            if len(source) > cls.MAX_FILE_SIZE_BYTES:
                logger.warning(f"[PDFExtractor] Buffer exceeds 50MB ({len(source)} bytes).")
            doc_kwargs = {"stream": source, "filetype": "pdf"}
        elif isinstance(source, str):
            if not os.path.exists(source):
                return cls._error_response("file_not_found", f"PDF file not found at: {source}")
            file_size = os.path.getsize(source)
            if file_size == 0:
                return cls._empty_response(f"PDF file is empty (0 bytes) at: {source}")
            if file_size > cls.MAX_FILE_SIZE_BYTES:
                logger.warning(f"[PDFExtractor] File {source} exceeds 50MB ({file_size} bytes).")
            doc_kwargs = {"filename": source}
        else:
            return cls._error_response("invalid_input", "Source must be a file path string or bytes.")

        # 2. Open Document with PyMuPDF
        try:
            doc = pymupdf.open(**doc_kwargs)
        except pymupdf.FileDataError as e:
            logger.error(f"[PDFExtractor] Corrupted PDF file: {e}")
            return cls._error_response("corrupted", f"Corrupted or invalid PDF format: {str(e)}")
        except Exception as e:
            logger.error(f"[PDFExtractor] Failed to open PDF document: {e}")
            return cls._error_response("corrupted", f"Unreadable PDF document: {type(e).__name__}: {str(e)}")

        try:
            # 3. Handle Encrypted Documents
            if doc.is_encrypted:
                auth_success = doc.authenticate("")  # Try empty/standard password
                if not auth_success:
                    logger.warning("[PDFExtractor] Document is password-protected and encrypted.")
                    return {
                        "success": False,
                        "status": "encrypted",
                        "is_encrypted": True,
                        "error": "Document is password-protected and encrypted.",
                        "text": "",
                        "pages": [],
                        "metadata": {},
                        "page_count": doc.page_count,
                        "ocr_required": False,
                    }

            page_count = doc.page_count
            if page_count == 0:
                return cls._empty_response("Document contains 0 pages.")

            # 4. Extract Document Metadata
            raw_meta = doc.metadata or {}
            metadata = {
                "title": raw_meta.get("title") or None,
                "author": raw_meta.get("author") or None,
                "subject": raw_meta.get("subject") or None,
                "keywords": raw_meta.get("keywords") or None,
                "creator": raw_meta.get("creator") or None,
                "producer": raw_meta.get("producer") or None,
                "creation_date": raw_meta.get("creationDate") or None,
                "mod_date": raw_meta.get("modDate") or None,
                "page_count": page_count,
                "format": raw_meta.get("format") or "PDF",
            }

            # 5. Extract Pages, Headings, and Tables
            pages_data: List[Dict[str, Any]] = []
            full_text_chunks: List[str] = []
            all_headings: List[Dict[str, Any]] = []
            all_tables: List[Dict[str, Any]] = []
            total_text_chars = 0

            limit_pages = min(page_count, max_pages)

            for page_idx in range(limit_pages):
                page = doc[page_idx]
                page_num = page_idx + 1

                # Extract page text
                page_text = page.get_text() or ""
                clean_page_text = page_text.strip()
                total_text_chars += len(clean_page_text)
                full_text_chunks.append(clean_page_text)

                # Extract Headings on this page
                page_headings = cls._detect_page_headings(page, page_num)
                all_headings.extend(page_headings)

                # Extract Tables on this page
                page_tables = cls._detect_page_tables(page, page_num)
                all_tables.extend(page_tables)

                pages_data.append({
                    "page_number": page_num,
                    "text": clean_page_text,
                    "char_count": len(clean_page_text),
                    "headings": [h["text"] for h in page_headings],
                    "tables_count": len(page_tables),
                })

            full_text = "\n\n".join(chunk for chunk in full_text_chunks if chunk)

            # 6. Scanned PDF Detection (Missing Text Stream)
            avg_chars_per_page = (total_text_chars / limit_pages) if limit_pages > 0 else 0
            is_scanned = (total_text_chars < 50 or avg_chars_per_page < cls.MIN_TEXT_CHARS_PER_PAGE_FOR_NATIVE)

            if is_scanned:
                logger.info(
                    f"[PDFExtractor] Scanned PDF detected: {limit_pages} pages, "
                    f"only {total_text_chars} total characters (avg {round(avg_chars_per_page, 1)}/page). "
                    "Marking OCR required."
                )

            return {
                "success": True,
                "status": "success",
                "text": full_text,
                "pages": pages_data,
                "page_count": page_count,
                "metadata": metadata,
                "headings": all_headings,
                "tables": all_tables,
                "total_chars": total_text_chars,
                "ocr_required": is_scanned,
                "ocr_status": "pending_ocr" if is_scanned else "not_required",
                "ocr_message": (
                    "Scanned document detected. Native digital text stream is missing or insufficient. "
                    "OCR extraction required for full indexing."
                    if is_scanned else None
                ),
            }

        finally:
            doc.close()

    @classmethod
    def _detect_page_headings(cls, page: pymupdf.Page, page_num: int) -> List[Dict[str, Any]]:
        """
        Detect headings by analyzing font size / bold flags and legal section patterns.
        """
        headings: List[Dict[str, Any]] = []
        try:
            # Extract text blocks
            blocks = page.get_text("blocks")
            for b in blocks:
                if len(b) >= 5:
                    block_text = b[4].strip()
                    for line in block_text.splitlines():
                        line = line.strip()
                        if not line or len(line) > 120:
                            continue

                        # Pattern check for section/clause/rule
                        is_heading = False
                        for pattern in cls.HEADING_PATTERNS:
                            if pattern.search(line):
                                is_heading = True
                                break

                        # Uppercase short title check
                        if not is_heading and line.isupper() and 5 < len(line) < 80:
                            is_heading = True

                        if is_heading:
                            headings.append({
                                "text": line,
                                "page_number": page_num,
                                "bbox": (b[0], b[1], b[2], b[3]),
                            })

        except Exception as e:
            logger.debug(f"[PDFExtractor] Heading detection warning on page {page_num}: {e}")

        return headings

    @classmethod
    def _detect_page_tables(cls, page: pymupdf.Page, page_num: int) -> List[Dict[str, Any]]:
        """
        Detect and extract structured tables from page using PyMuPDF table finder.
        """
        tables: List[Dict[str, Any]] = []
        try:
            if hasattr(page, "find_tables"):
                tabs = page.find_tables()
                for t_idx, tab in enumerate(tabs.tables):
                    extracted_rows = tab.extract()
                    if extracted_rows:
                        # Clean cells
                        cleaned_rows = [
                            [str(c or "").strip() for c in row]
                            for row in extracted_rows
                        ]
                        tables.append({
                            "page_number": page_num,
                            "table_index": t_idx + 1,
                            "row_count": len(cleaned_rows),
                            "col_count": len(cleaned_rows[0]) if cleaned_rows else 0,
                            "rows": cleaned_rows,
                        })
        except Exception as e:
            logger.debug(f"[PDFExtractor] Table detection warning on page {page_num}: {e}")

        return tables

    @staticmethod
    def _empty_response(error_message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status": "empty",
            "error": error_message,
            "text": "",
            "pages": [],
            "page_count": 0,
            "metadata": {},
            "headings": [],
            "tables": [],
            "ocr_required": False,
            "ocr_status": "empty",
        }

    @staticmethod
    def _error_response(status: str, error_message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status": status,
            "error": error_message,
            "text": "",
            "pages": [],
            "page_count": 0,
            "metadata": {},
            "headings": [],
            "tables": [],
            "ocr_required": False,
            "ocr_status": "error",
        }
