"""
PolicySetu — MahaDBT Source Adapter
====================================
Official source adapter for Maharashtra MahaDBT scholarship portals:
- MahaDBT Main Portal: https://mahadbt.maharashtra.gov.in/
- MahaDBT Scheme Listing: https://mahadbt.maharashtra.gov.in/Home/Index
- MahaDBT 2.0 (AY 2026-27 Application Engine): https://mahadbt2.maharashtra.gov.in/
- Social Justice & Special Assistance: https://sjsa.maharashtra.gov.in/en/service/mahadbt/

Features:
- SSRF-safe HTTP client with timeouts, retry backoff, and rate limiting.
- Extraction of official schemes across all listed departments:
  * Social Justice and Special Assistance
  * Tribal Development
  * Directorate of Higher Education (DHE)
  * Directorate of Technical Education (DTE)
  * School Education and Sports
  * OBC, SEBC, VJNT & SBC Welfare
  * Minority Development
  * Medical Education and Research (DMER)
- Academic Year distinction: Points fresh/renewal applications to MahaDBT 2.0.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from app.adapters.base_adapter import BaseSourceAdapter
from app.models.document import DOC_TYPE_SCHEME
from app.utils.helpers import utc_now, hash_content

logger = logging.getLogger("policysetu.adapters.mahadbt")

MAHADBT_BASE_URL = "https://mahadbt.maharashtra.gov.in"
MAHADBT_HOME_INDEX = "https://mahadbt.maharashtra.gov.in/Home/Index"
MAHADBT2_PORTAL_URL = "https://mahadbt2.maharashtra.gov.in"
MAHADBT2_COLLEGE_URL = "https://mahadbt2.maharashtra.gov.in/college-student"
MAHADBT2_GUIDELINES_URL = "https://mahadbt2.maharashtra.gov.in/documents/20118/8641165/DBTGuidelines.pdf"


class MahaDBTAdapter(BaseSourceAdapter):
    """
    Adapter for official Maharashtra MahaDBT scholarship portals.
    """

    def __init__(self):
        super().__init__(
            source_name="MahaDBT Scholarship Portal",
            base_url=MAHADBT_BASE_URL,
            source_code="mahadbt",
            timeout=15,
            rate_limit_delay=1.0,
        )

    def fetch_recent_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Crawl accessible scheme listings from official MahaDBT and MahaDBT 2.0 pages.
        """
        schemes: List[Dict[str, Any]] = []
        seen_names = set()

        # 1. Fetch from MahaDBT Home/Index
        try:
            resp = self.safe_get(MAHADBT_HOME_INDEX)
            soup = BeautifulSoup(resp.text, "html.parser")
            accordions = soup.find_all(class_="allschemes")
            for acc in accordions:
                dept_name = acc.get_text(strip=True)
                panel = acc.find_next_sibling()
                if not panel:
                    continue
                for a in panel.find_all("a"):
                    s_name = a.get_text(strip=True)
                    if not s_name or s_name in seen_names:
                        continue
                    seen_names.add(s_name)
                    href = a.get("href", "")
                    canonical = urljoin(MAHADBT_BASE_URL, href) if href and not href.startswith("javascript:") else f"{MAHADBT_HOME_INDEX}#{dept_name.lower().replace(' ', '_')}"
                    schemes.append({
                        "scheme_name": s_name,
                        "department": dept_name,
                        "jurisdiction": "Maharashtra",
                        "state": "Maharashtra",
                        "category": "Education",
                        "canonical_url": canonical,
                        "official_scheme_url": MAHADBT_HOME_INDEX,
                        "official_url": MAHADBT2_PORTAL_URL,
                        "source_name": "MahaDBT (Government of Maharashtra)",
                        "academic_year": "2026-27",
                        "application_status": "Active (AY 2026-27 on MahaDBT 2.0)",
                        "official_guidelines_url": MAHADBT2_GUIDELINES_URL,
                    })
        except Exception as e:
            logger.warning(f"[MahaDBT] Error fetching from {MAHADBT_HOME_INDEX}: {e}")

        # 2. Fetch from MahaDBT 2.0 college-student table if accessible
        try:
            resp2 = self.safe_get(MAHADBT2_COLLEGE_URL)
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            table = soup2.find("table")
            if table:
                for tr in table.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 3:
                        dept = tds[0].get_text(" ", strip=True)
                        name = tds[2].get_text(" ", strip=True)
                        if name and name not in seen_names:
                            seen_names.add(name)
                            # check if GR link is present in modal
                            gr_links = [a.get("href") for a in tr.find_all("a") if a.get("href")]
                            gr_url = urljoin(MAHADBT2_PORTAL_URL, gr_links[0]) if gr_links else MAHADBT2_GUIDELINES_URL
                            schemes.append({
                                "scheme_name": name,
                                "department": dept,
                                "jurisdiction": "Maharashtra",
                                "state": "Maharashtra",
                                "category": "Education",
                                "canonical_url": f"{MAHADBT2_COLLEGE_URL}#{name.lower().replace(' ', '_')}",
                                "official_scheme_url": MAHADBT_HOME_INDEX,
                                "official_url": MAHADBT2_PORTAL_URL,
                                "source_name": "MahaDBT 2.0 (Government of Maharashtra)",
                                "academic_year": "2026-27",
                                "application_status": "Active (AY 2026-27 on MahaDBT 2.0)",
                                "official_guidelines_url": gr_url,
                            })
        except Exception as e:
            logger.warning(f"[MahaDBT] Error fetching from {MAHADBT2_COLLEGE_URL}: {e}")

        return schemes[:limit]

    def parse_document(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize raw scheme payload into the canonical PolicyDocument schema.
        """
        scheme_name = raw_item.get("scheme_name") or raw_item.get("title")
        if not scheme_name:
            return None

        dept = raw_item.get("department", "Social Justice and Special Assistance")
        desc = raw_item.get("description") or f"Official scholarship scheme administered by the {dept}, Government of Maharashtra."
        elig = raw_item.get("eligibility_criteria") or "Eligible students must be permanent residents of Maharashtra enrolled in recognized courses."

        content_body = (
            f"SCHEME NAME: {scheme_name}\n"
            f"ADMINISTERING DEPARTMENT: {dept}\n"
            f"JURISDICTION: Maharashtra\n"
            f"ACADEMIC YEAR: {raw_item.get('academic_year', '2026-27')}\n"
            f"APPLICATION STATUS: {raw_item.get('application_status', 'Active (AY 2026-27 on MahaDBT 2.0)')}\n"
            f"INCOME LIMIT: {raw_item.get('income_limit', 'Refer to department guidelines')}\n"
            f"CASTE CATEGORY: {raw_item.get('caste_category', 'All eligible categories')}\n"
            f"COURSE CRITERIA: {raw_item.get('course_criteria', 'Recognized Post-Matric / Higher Education Courses')}\n"
            f"BENEFITS: {raw_item.get('benefit_details', 'Tuition fee waiver, exam fee reimbursement, and maintenance allowance')}\n"
            f"REQUIRED DOCUMENTS: {raw_item.get('required_documents', 'Aadhaar Card, Domicile Certificate, Income Certificate, Caste Certificate, Marksheets')}\n\n"
            f"ELIGIBILITY CRITERIA:\n{elig}\n\n"
            f"OFFICIAL NOTICE:\nFresh and renewal scholarship applications for Academic Year 2026-27 are processed exclusively through MahaDBT 2.0 (https://mahadbt2.maharashtra.gov.in/).\n"
        )

        return {
            "title": scheme_name,
            "canonical_url": self.normalize_canonical_url(raw_item.get("canonical_url", f"https://mahadbt.maharashtra.gov.in/schemes/{hash_content(scheme_name)[:12]}")),
            "official_url": raw_item.get("official_url") or MAHADBT2_PORTAL_URL,
            "source_listing_url": raw_item.get("official_scheme_url") or MAHADBT_HOME_INDEX,
            "department": dept,
            "jurisdiction": "Maharashtra",
            "state": "Maharashtra",
            "document_type": DOC_TYPE_SCHEME,
            "category": "Education",
            "language": "en",
            "content": content_body,
            "content_hash": hash_content(content_body),
            "ai_summary": elig[:300] if len(elig) > 300 else elig,
            "is_verified": True,
            "classification_status": "verified_policy",
            "processing_status": "completed",
            "detected_at": utc_now(),
            "first_detected_at": utc_now(),
        }
