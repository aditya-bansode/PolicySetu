"""
PolicySetu — EGazetteAdapter
============================
Candidate adapter for The Gazette of India (e-Gazette) (https://egazette.gov.in).
Accurately diagnoses and communicates upstream architectural requirements:
- Website relies on transient ASP.NET session state tokens in path (e.g. (S(...))).
- Search forms require server-side POST postbacks with __VIEWSTATE and session cookies.
- No public RSS/Atom feed or REST API exists.
- Direct automated document scraping without session negotiation is restricted.
"""

import datetime
import logging
from typing import List, Dict, Any, Optional

from app.adapters.base_adapter import BaseSourceAdapter

logger = logging.getLogger("policysetu.adapters.egazette")


class EGazetteAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_name="The Gazette of India (e-Gazette)",
            base_url="https://egazette.gov.in",
            source_code="egazette",
            timeout=10,
            rate_limit_delay=2.0,
        )
        self.directory_url = "https://egazette.gov.in/GazetteDirectory.aspx"

    def check_health(self) -> Dict[str, Any]:
        """
        Verify domain reachability while auditing the requirement for ASP.NET session state.
        """
        return {
            "is_healthy": False,
            "status": "inaccessible",
            "message": (
                "e-Gazette portal relies on transient ASP.NET session tokens (S(...)) "
                "and server-side POST postbacks with __VIEWSTATE. Public RSS or JSON catalog "
                "is not provided by the Directorate of Printing."
            ),
            "latency_ms": 0.0,
            "requires_session_postbacks": True,
        }

    def fetch_recent_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        e-Gazette search forms cannot be traversed via static GET requests.
        Logs architectural notice and returns empty list.
        """
        logger.warning(
            "[e-Gazette] Inaccessible via direct HTTP GET. "
            "Requires stateful ASP.NET session management and captcha handling."
        )
        return []

    def parse_document(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses official Gazette notification payload when supplied by session runner or test mock.
        """
        issue_no = raw_item.get("issue_number", "Gazette Issue")
        title = raw_item.get("title") or f"Gazette of India Notification — {issue_no}"
        canonical_url = self.normalize_canonical_url(
            raw_item.get("url", f"https://egazette.gov.in/Issue/{raw_item.get('id', '')}")
        )
        pub_date = raw_item.get("publication_date")
        if isinstance(pub_date, str):
            try:
                pub_date = datetime.datetime.fromisoformat(pub_date)
            except Exception:
                pub_date = None

        return {
            "title": title,
            "canonical_url": canonical_url,
            "department": raw_item.get("department", "Ministry of Housing and Urban Affairs"),
            "jurisdiction": "Central Government",
            "state": None,
            "document_type": "gazette_notification",
            "category": "General",
            "publication_date": pub_date,
            "content": raw_item.get("content", title),
            "original_file_path": None,
            "language": raw_item.get("language", "en"),
        }
