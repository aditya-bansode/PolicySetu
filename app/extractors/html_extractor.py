"""
PolicySetu — HTML Policy Document Extractor
===========================================
Extracts clean plain text, semantic headings, tables, and metadata
from HTML government notifications, gazette pages, and press releases.
Strips boilerplate (scripts, navbars, footers, sidebars).
"""

import re
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from html import unescape

logger = logging.getLogger("policysetu.extractors.html")


class HTMLExtractor:
    """
    Robust HTML policy content extractor with semantic heading and table support.
    """

    BOILERPLATE_TAGS = [
        "script", "style", "nav", "header", "footer", "aside",
        "noscript", "form", "iframe", "svg"
    ]

    @classmethod
    def extract(cls, html_content: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured text, headings, tables, and metadata from raw HTML.
        """
        if not html_content or not html_content.strip():
            return {
                "success": False,
                "status": "empty",
                "error": "HTML content is empty.",
                "text": "",
                "headings": [],
                "tables": [],
                "metadata": {},
            }

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. Extract Document Metadata
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": lambda n: n and n.lower() in ("description", "og:description")})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"].strip()

            meta_author = ""
            author_tag = soup.find("meta", attrs={"name": lambda n: n and n.lower() in ("author", "creator")})
            if author_tag and author_tag.get("content"):
                meta_author = author_tag["content"].strip()

            metadata = {
                "title": title,
                "description": meta_desc,
                "author": meta_author,
                "base_url": base_url,
            }

            # 2. Extract Headings before stripping tags
            headings: List[Dict[str, Any]] = []
            for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                htext = h.get_text(strip=True)
                if htext and len(htext) > 2:
                    headings.append({
                        "level": int(h.name[1]),
                        "text": htext,
                    })

            # 3. Extract Tables
            tables: List[Dict[str, Any]] = []
            for t_idx, table in enumerate(soup.find_all("table")):
                rows = []
                for tr in table.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
                    if cells:
                        rows.append(cells)
                if rows:
                    tables.append({
                        "table_index": t_idx + 1,
                        "row_count": len(rows),
                        "rows": rows,
                    })

            # 4. Remove boilerplate elements
            for tag in soup.find_all(cls.BOILERPLATE_TAGS):
                tag.decompose()

            # Target main content container if available
            main_container = soup.find(["main", "article"]) or soup.find(id=lambda i: i and any(k in i.lower() for k in ("content", "body", "article", "innner", "pdfdiv")))
            content_root = main_container if main_container else soup.body or soup

            # Convert structure into plain text with paragraph separation
            raw_text = content_root.get_text(separator="\n", strip=True)
            cleaned_text = cls.clean_text(raw_text)

            return {
                "success": True,
                "status": "success",
                "text": cleaned_text,
                "headings": headings,
                "tables": tables,
                "metadata": metadata,
                "char_count": len(cleaned_text),
            }

        except Exception as e:
            logger.error(f"[HTMLExtractor] Error extracting HTML: {e}")
            return {
                "success": False,
                "status": "error",
                "error": f"Failed to parse HTML: {type(e).__name__}: {str(e)}",
                "text": "",
                "headings": [],
                "tables": [],
                "metadata": {},
            }

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize line breaks, whitespaces, and decode entities."""
        if not text:
            return ""
        text = unescape(text)
        # Collapse excessive spaces
        text = re.sub(r"[ \t]+", " ", text)
        # Collapse excessive line breaks (max 2 consecutive newlines)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()
