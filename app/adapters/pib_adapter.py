"""
PolicySetu — PIBSourceAdapter
=============================
Verified production adapter for Press Information Bureau (PIB) releases.
Monitors AllRel.aspx and extracts ministerial notifications, cabinet decisions,
and official policy announcements.
"""

import datetime
import logging
import re
import urllib.parse
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.adapters.base_adapter import BaseSourceAdapter

logger = logging.getLogger("policysetu.adapters.pib")


class PIBSourceAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_name="Press Information Bureau",
            base_url="https://pib.gov.in",
            source_code="pib",
            timeout=15,
            rate_limit_delay=1.0,
        )
        self.listing_url = "https://pib.gov.in/AllRel.aspx"

    def fetch_recent_documents(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Scrape recent press releases from PIB AllRel.aspx.
        """
        items: List[Dict[str, Any]] = []
        try:
            resp = self.safe_get(self.listing_url)
            soup = BeautifulSoup(resp.content, "html.parser")

            # Collect release links
            seen_prids = set()
            for a in soup.find_all("a"):
                href = a.get("href", "")
                if "PRID=" in href:
                    match = re.search(r"PRID=(\d+)", href, re.IGNORECASE)
                    if match:
                        prid = match.group(1)
                        if prid in seen_prids:
                            continue
                        seen_prids.add(prid)

                        title = a.get_text(strip=True)
                        if not title:
                            continue

                        canonical_url = f"https://pib.gov.in/PressReleaseDetail.aspx?PRID={prid}"
                        items.append({
                            "prid": prid,
                            "title": title,
                            "url": canonical_url,
                            "href": href,
                        })
                        if len(items) >= limit:
                            break

            logger.info(f"[PIB] Successfully discovered {len(items)} recent press releases.")
        except Exception as e:
            logger.error(f"[PIB] Error retrieving document listings: {e}")
            raise

        return items

    def _parse_publication_date(self, text: str) -> Optional[datetime.datetime]:
        """
        Parse publication date from PIB's PrDateTime container.
        Example: 'प्रविष्टि तिथि: 15 NOV 2026 3:31PM by PIB Delhi'
        Never invents dates: returns None if unparseable.
        """
        if not text:
            return None

        # Extract date-like substring e.g. '15 NOV 2026 3:31PM' or '15 NOV 2026'
        match = re.search(r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM)?)?)", text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            try:
                dt = date_parser.parse(candidate)
                # Store in UTC naive
                return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
            except Exception:
                pass
        return None

    def parse_document(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch release detail from PIB iframe view and extract clean content.
        """
        prid = raw_item.get("prid")
        raw_title = raw_item.get("title", "")
        canonical_url = self.normalize_canonical_url(raw_item.get("url", f"https://pib.gov.in/PressReleaseDetail.aspx?PRID={prid}"))

        content_text = ""
        department = "Government of India"
        pub_date: Optional[datetime.datetime] = None
        detected_language = "hi" if re.search(r"[\u0900-\u097F]", raw_title) else "en"

        try:
            # Query the clean iframe content endpoint
            iframe_url = f"https://pib.gov.in/PressReleaseIframePage.aspx?PRID={prid}"
            resp = self.safe_get(iframe_url)
            soup = BeautifulSoup(resp.content, "html.parser")

            # Extract title if better element available
            heading = soup.find(class_=lambda c: c and "event-heading" in str(c))
            if heading and heading.get_text(strip=True):
                raw_title = heading.get_text(strip=True)

            # Extract publication date
            date_el = soup.find(id="PrDateTime") or soup.find(class_=lambda c: c and "date" in str(c).lower())
            if date_el:
                pub_date = self._parse_publication_date(date_el.get_text(strip=True))

            # Extract ministry/department
            container = soup.find(class_="innner-page-main-about-us-content-right-part") or soup.find("div", class_="container")
            if container:
                # Top header before event heading is usually ministry
                first_div = container.find("div")
                if first_div and first_div != heading:
                    dept_candidate = first_div.get_text(strip=True)
                    if dept_candidate and len(dept_candidate) < 120 and "PRID" not in dept_candidate:
                        department = dept_candidate

            # Extract body text from PdfDiv or main container
            pdf_div = soup.find(id="PdfDiv")
            if pdf_div:
                content_text = pdf_div.get_text(separator="\n", strip=True)
            elif container:
                content_text = container.get_text(separator="\n", strip=True)
            else:
                content_text = raw_title

            # Re-check language from content
            if re.search(r"[\u0900-\u097F]", content_text[:300]):
                detected_language = "hi"
            else:
                detected_language = "en"

        except Exception as e:
            logger.warning(f"[PIB] Could not fetch detailed content for PRID {prid}: {e}")
            content_text = raw_title

        return {
            "title": raw_title,
            "canonical_url": canonical_url,
            "department": department,
            "jurisdiction": "Central Government",
            "state": None,
            "document_type": "press_release",
            "category": "General",
            "publication_date": pub_date,
            "content": content_text or raw_title,
            "original_file_path": None,
            "language": detected_language,
        }
