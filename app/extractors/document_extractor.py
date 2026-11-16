"""
PolicySetu — Unified Document Extractor Facade
==============================================
Convenience facade delegating to specialized PDFExtractor and HTMLExtractor engines.
"""

from typing import Dict, Any, Union, Optional
from app.extractors.pdf_extractor import PDFExtractor
from app.extractors.html_extractor import HTMLExtractor


class DocumentExtractor:
    """
    Unified entry point for extracting text from PDFs and HTML government documents.
    """

    @staticmethod
    def extract_from_pdf(source: Union[str, bytes], max_pages: int = 500) -> Dict[str, Any]:
        """Extract text, metadata, headings, and tables from PDF."""
        return PDFExtractor.extract(source, max_pages=max_pages)

    @staticmethod
    def extract_from_html(html_content: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Extract clean text, metadata, headings, and tables from HTML."""
        return HTMLExtractor.extract(html_content, base_url=base_url)

    @staticmethod
    def extract_text_from_html(html_content: str) -> str:
        """Backward-compatible helper returning plain text."""
        res = HTMLExtractor.extract(html_content)
        return res.get("text", "")

    @staticmethod
    def extract_key_provisions(text: str) -> list[str]:
        """Extract key bullet points or numbered provisions."""
        import re
        provisions = []
        for line in text.splitlines():
            line = line.strip()
            if (line.startswith("•") or line.startswith("-") or re.match(r"^\d+[\.\)]", line)) and len(line) > 15:
                provisions.append(re.sub(r"^[•\-\d\.\)]+\s*", "", line))
        return provisions[:10]
