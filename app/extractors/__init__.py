"""
PolicySetu — Extractors Package
"""
from app.extractors.pdf_extractor import PDFExtractor
from app.extractors.html_extractor import HTMLExtractor
from app.extractors.document_extractor import DocumentExtractor

__all__ = ["PDFExtractor", "HTMLExtractor", "DocumentExtractor"]
