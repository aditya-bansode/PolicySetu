"""
PolicySetu — MaharashtraGRAdapter
=================================
Verified production adapter for Maharashtra Government Resolutions (शासन निर्णय).
Monitors https://gr.maharashtra.gov.in/1145/Government-Resolutions, parses official
gazetted tables, extracts dates, departments, unique codes, and official PDF URLs.
"""

import time
import datetime
import logging
import re
import urllib.parse
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from app.adapters.base_adapter import BaseSourceAdapter

logger = logging.getLogger("policysetu.adapters.maharashtra_gr")


class MaharashtraGRAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_name="Maharashtra Government Resolutions",
            base_url="https://gr.maharashtra.gov.in",
            source_code="maharashtra_gr",
            timeout=15,
            rate_limit_delay=1.0,
        )
        self.listing_url = "https://gr.maharashtra.gov.in/1145/Government-Resolutions"

    def check_health(self) -> Dict[str, Any]:
        """Probe the verified Government-Resolutions listing endpoint directly."""
        start = time.time()
        try:
            resp = self.safe_get(self.listing_url, timeout=12)
            latency = (time.time() - start) * 1000
            return {
                "is_healthy": True,
                "status": "active",
                "message": f"HTTP {resp.status_code} OK (Table Reachable)",
                "latency_ms": round(latency, 2),
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "is_healthy": False,
                "status": "degraded",
                "message": f"{type(e).__name__}: {str(e)}",
                "latency_ms": round(latency, 2),
            }


    def fetch_recent_documents(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Scrape recent government resolutions from Maharashtra GR table.
        """
        items: List[Dict[str, Any]] = []
        try:
            resp = self.safe_get(self.listing_url)
            soup = BeautifulSoup(resp.content, "html.parser")

            tables = soup.find_all("table")
            if not tables:
                logger.warning("[MaharashtraGR] No table elements found on listing page.")
                return items

            # The GR entries are in the second table (or largest table)
            gr_table = tables[1] if len(tables) > 1 else tables[0]
            rows = gr_table.find_all("tr")

            for r in rows:
                cols = r.find_all(["td"])
                if len(cols) < 5:
                    continue

                sr_no = cols[0].get_text(strip=True)
                dept = cols[1].get_text(strip=True)
                title = cols[2].get_text(strip=True)
                gr_code = cols[3].get_text(strip=True)
                gr_date_str = cols[4].get_text(strip=True)

                if not title or not gr_code:
                    continue

                # Locate PDF download link
                pdf_link = None
                for a in r.find_all("a"):
                    href = a.get("href", "")
                    if ".pdf" in href.lower() or "upload" in href.lower():
                        # Resolve relative path
                        resolved = urllib.parse.urljoin(self.listing_url, href)
                        pdf_link = resolved
                        break

                if not pdf_link:
                    # Construct default canonical path if link was omitted from row
                    pdf_link = f"https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/Marathi/{gr_code}.pdf"

                items.append({
                    "sr_no": sr_no,
                    "department": dept,
                    "title": title,
                    "gr_code": gr_code,
                    "gr_date_str": gr_date_str,
                    "url": pdf_link,
                    "canonical_url": pdf_link,
                    "pdf_url": pdf_link,
                })


                if len(items) >= limit:
                    break

            logger.info(f"[MaharashtraGR] Discovered {len(items)} government resolutions from table.")
        except Exception as e:
            logger.error(f"[MaharashtraGR] Error fetching GR table: {e}")
            raise

        return items

    def _parse_gr_date(self, date_str: str) -> Optional[datetime.datetime]:
        """
        Parse Maharashtra GR date string formatted as DD-MM-YYYY.
        Never invents dates.
        """
        if not date_str:
            return None
        clean_str = date_str.strip()
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(clean_str, fmt)
            except ValueError:
                pass
        return None

    def parse_document(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform raw GR row into PolicySetu document schema.
        Optionally downloads the PDF bytes or stores content metadata.
        """
        raw_title = raw_item.get("title", "")
        raw_dept = raw_item.get("department", "महाराष्ट्र शासन")
        gr_code = raw_item.get("gr_code", "")
        pdf_url = raw_item.get("pdf_url", "")
        canonical_url = self.normalize_canonical_url(pdf_url)

        pub_date = self._parse_gr_date(raw_item.get("gr_date_str", ""))

        # Compose authoritative content representation
        content_text = (
            f"महाराष्ट्र शासन निर्णय (Government Resolution)\n"
            f"सांकेतांक क्रमांक: {gr_code}\n"
            f"विभाग: {raw_dept}\n"
            f"दिनांक: {raw_item.get('gr_date_str', 'N/A')}\n\n"
            f"शीर्षक: {raw_title}\n\n"
            f"अधिकृत शासन निर्णय दस्तावेज: {canonical_url}\n"
        )

        # Categorization heuristic based on department keywords
        category = "General"
        dept_lower = raw_dept.lower()
        if "कृषी" in dept_lower or "शेती" in dept_lower or "पशुसंवर्धन" in dept_lower:
            category = "Agriculture"
        elif "उद्योग" in dept_lower or "कौशल्य" in dept_lower or "रोजगार" in dept_lower:
            category = "Commerce & Industry"
        elif "आरोग्य" in dept_lower:
            category = "Health & Family Welfare"
        elif "शिक्षण" in dept_lower or "शालेय" in dept_lower:
            category = "Education"
        elif "वित्त" in dept_lower or "महसूल" in dept_lower:
            category = "Finance & Taxation"
        elif "प्रशासन" in dept_lower or "सेवा" in dept_lower:
            category = "Administration"

        # Download permitted PDF, deduplicate store, and extract text
        original_file_path = None
        try:
            if pdf_url and pdf_url.startswith("http"):
                pdf_resp = self.safe_get(pdf_url, timeout=10)
                if pdf_resp.status_code == 200 and pdf_resp.content.startswith(b"%PDF"):
                    from app.storage.document_storage import DocumentStorageManager
                    from app.extractors.document_extractor import DocumentExtractor
                    storage = DocumentStorageManager()
                    saved = storage.save_document(
                        pdf_resp.content,
                        filename_hint=f"{gr_code}.pdf",
                        source_id=6,
                    )
                    original_file_path = saved["file_path"]
                    extracted = DocumentExtractor.extract_from_pdf(pdf_resp.content)
                    if extracted.get("success") and extracted.get("text"):
                        content_text = f"{content_text}\n\n[Extracted Resolution Content]\n{extracted['text']}"
        except Exception as e:
            logger.debug(f"[MaharashtraGR] PDF download/extraction notice: {e}")

        return {
            "title": raw_title,
            "canonical_url": canonical_url,
            "department": raw_dept,
            "jurisdiction": "State Government",
            "state": "Maharashtra",
            "document_type": "government_resolution",
            "category": category,
            "publication_date": pub_date,
            "content": content_text,
            "original_file_path": original_file_path,
            "language": "mr",
        }

