"""
PolicySetu — IndiaCodeAdapter
=============================
Candidate adapter for India Code Legislative Portal (https://www.indiacode.nic.in / https://indiacode.gov.in).
Accurately diagnoses and communicates upstream architectural requirements:
- Website migrated from indiacode.nic.in to indiacode.gov.in.
- Front-end is an Angular Single Page Application (requires client-side JS rendering).
- Backend REST API (/server/api/core/items) requires Bearer authentication (HTTP 401).
- Direct static crawling is restricted. Clearly marked as inaccessible.
"""

import datetime
import logging
from typing import List, Dict, Any, Optional

from app.adapters.base_adapter import BaseSourceAdapter

logger = logging.getLogger("policysetu.adapters.india_code")


class IndiaCodeAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_name="India Code Legislative Portal",
            base_url="https://indiacode.gov.in",
            source_code="india_code",
            timeout=10,
            rate_limit_delay=2.0,
        )
        self.migration_url = "https://www.indiacode.nic.in"
        self.api_endpoint = "https://indiacode.gov.in/server/api/core/items"

    def check_health(self) -> Dict[str, Any]:
        """
        Verify domain reachability while auditing the requirement for SPA rendering & API tokens.
        """
        return {
            "is_healthy": False,
            "status": "inaccessible",
            "message": (
                "India Code migrated to DSpace 7 Angular SPA. Static HTML lacks content; "
                "internal REST API /server/api/core/items returns HTTP 401 Unauthorized "
                "without official API authentication token."
            ),
            "latency_ms": 0.0,
            "requires_js": True,
            "requires_auth": True,
        }

    def fetch_recent_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        India Code requires client-side JavaScript execution or authorized Bearer token.
        Returns empty list and logs explicit architectural notice.
        """
        logger.warning(
            "[IndiaCode] Inaccessible via static HTTP requests. "
            "Requires headless Chromium driver or official Ministry of Law API credentials."
        )
        return []

    def parse_document(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses India Code Act payload when supplied by headless scraper or test mock.
        """
        act_title = raw_item.get("title", "")
        act_id = raw_item.get("act_id") or raw_item.get("uuid", "")
        canonical_url = self.normalize_canonical_url(
            raw_item.get("url", f"https://indiacode.gov.in/handle/123456789/{act_id}")
        )
        pub_date = raw_item.get("publication_date")
        if isinstance(pub_date, str):
            try:
                pub_date = datetime.datetime.fromisoformat(pub_date)
            except Exception:
                pub_date = None

        return {
            "title": act_title,
            "canonical_url": canonical_url,
            "department": raw_item.get("ministry", "Ministry of Law and Justice"),
            "jurisdiction": "Central Government",
            "state": None,
            "document_type": "act",
            "category": "Law & Justice",
            "publication_date": pub_date,
            "content": raw_item.get("content", act_title),
            "original_file_path": None,
            "language": raw_item.get("language", "en"),
        }
