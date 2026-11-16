"""
PolicySetu — BaseSourceAdapter
==============================
Abstract interface and resilient communication foundation for all official
government portal and gazette crawlers.

Security Guarantees:
- Server-Side Request Forgery (SSRF) defense: blocks loopback, private, link-local, and internal IPs.
- Respectful rate limiting and exponential retry policies.
- Request timeout enforcement on all outbound HTTP calls.
"""

from abc import ABC, abstractmethod
import datetime
import ipaddress
import logging
import re
import socket
import ssl
import time
import urllib.parse
from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.helpers import hash_content, utc_now

logger = logging.getLogger("policysetu.adapters")


class BaseSourceAdapter(ABC):
    """
    Standard interface for all verified government source adapters.
    Guarantees resilient HTTP requests, rate limiting, URL normalization,
    consistent error isolation, and SSRF defense.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
        "PolicySetu-Monitor/1.0"
    )

    def __init__(
        self,
        source_name: str,
        base_url: str,
        source_code: str,
        timeout: int = 15,
        rate_limit_delay: float = 1.0,
    ):
        self.source_name = source_name
        self.base_url = base_url
        self.source_code = source_code
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

        # Configure resilient session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8,mr;q=0.7",
        })

        # Exponential backoff retry strategy for transient errors
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _apply_rate_limit(self) -> None:
        """Enforce respectful delay between consecutive requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def validate_url_for_ssrf(url: str) -> None:
        """
        Validate that the target URL is safe and does not target loopback,
        private, link-local (cloud metadata), or internal networks.
        """
        if not url:
            raise ValueError("URL cannot be empty.")
        parsed = urllib.parse.urlsplit(url.strip())
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(f"SSRF Protection: Scheme '{parsed.scheme}' is forbidden. Only HTTP/HTTPS permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("SSRF Protection: Invalid URL hostname.")

        # Check common forbidden hostnames and cloud metadata addresses
        blocked_hosts = {
            "localhost", "127.0.0.1", "::1", "0.0.0.0",
            "metadata.google.internal", "169.254.169.254"
        }
        if hostname.lower() in blocked_hosts:
            raise ValueError(f"SSRF Protection: Connection to internal/metadata host '{hostname}' is blocked.")

        try:
            # Check resolved IP address
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip = ipaddress.ip_address(ip_str)
                if (
                    ip.is_loopback or
                    ip.is_private or
                    ip.is_link_local or
                    ip.is_multicast or
                    ip.is_unspecified
                ):
                    raise ValueError(f"SSRF Protection: Connection to private/internal IP {ip_str} is blocked.")

                if ip.is_reserved:
                    # RFC 6052 Well-Known Prefix for IPv4-IPv6 translation (64:ff9b::/96)
                    nat64_prefix = ipaddress.ip_network("64:ff9b::/96")
                    if ip.version == 6 and ip in nat64_prefix:
                        # Extract lower 32 bits as IPv4 and verify it is not private/loopback
                        ipv4_int = int(ip) & 0xFFFFFFFF
                        embedded_v4 = ipaddress.IPv4Address(ipv4_int)
                        if (
                            embedded_v4.is_private or
                            embedded_v4.is_loopback or
                            embedded_v4.is_link_local or
                            embedded_v4.is_unspecified
                        ):
                            raise ValueError(f"SSRF Protection: Connection to private embedded IP {embedded_v4} via NAT64 is blocked.")
                    else:
                        raise ValueError(f"SSRF Protection: Connection to reserved IP {ip_str} is blocked.")
        except socket.gaierror as e:
            # DNS resolution error handled naturally during request
            logger.debug(f"SSRF DNS check resolution note for {hostname}: {e}")

    def safe_get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """
        Execute an HTTP GET request with SSRF validation, rate limiting, timeouts, and graceful error handling.
        """
        self.validate_url_for_ssrf(url)
        self._apply_rate_limit()
        kwargs.setdefault("timeout", self.timeout)
        try:
            resp = self.session.get(url, params=params, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.SSLError:
            # Fallback for government sites with misconfigured intermediate cert chains
            logger.warning(f"[{self.source_code}] SSL certificate verification failed for {url}. Attempting unverified fallback.")
            resp = self.session.get(url, params=params, verify=False, **kwargs)
            resp.raise_for_status()
            return resp

    @staticmethod
    def normalize_canonical_url(url: str) -> str:
        """
        Normalize canonical URLs by stripping analytics trackers, fragments,
        redundant default ports, and normalizing paths.
        """
        if not url:
            return ""
        parsed = urllib.parse.urlsplit(url.strip())

        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Strip tracking query parameters
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "fbclid", "gclid", "_ga", "ref", "sessionid", "jsessionid"
        }
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_query = [
            (k, v) for k, v in query_pairs
            if k.lower() not in tracking_params and not k.lower().startswith("utm_")
        ]
        new_query = urllib.parse.urlencode(filtered_query)

        # Remove trailing slash from path unless it's just '/'
        path = parsed.path
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        return urllib.parse.urlunsplit((scheme, netloc, path, new_query, ""))

    def check_health(self) -> Dict[str, Any]:
        """
        Probe portal endpoint to verify reachability and measure response latency.
        """
        start = time.time()
        try:
            resp = self.safe_get(self.base_url, timeout=10)
            latency = (time.time() - start) * 1000
            return {
                "is_healthy": True,
                "status": "active",
                "message": f"HTTP {resp.status_code} OK",
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

    @abstractmethod
    def fetch_recent_documents(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch newly published policies or documents from the target source.
        Returns a list of raw or semi-structured items.
        """
        pass

    @abstractmethod
    def parse_document(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a crawled payload into the standardized PolicySetu document schema.
        """
        pass
