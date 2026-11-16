"""
PolicySetu — API Rate Limiter
=============================
Thread-safe sliding window rate limiting for public Flask APIs.
Protects endpoints against brute-force and resource exhaustion attacks.
"""

import time
import threading
from functools import wraps
from typing import Dict, List, Tuple
from flask import request
from app.utils.helpers import api_response

_lock = threading.Lock()
# IP -> list of request timestamps (epoch floats)
_ip_buckets: Dict[str, List[float]] = {}


def rate_limit(requests_per_minute: int = 60, burst_limit: int = 15):
    """
    Decorator to enforce per-IP rate limits using a 60-second sliding window.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Bypass rate limit during automated test runs
            from flask import current_app
            if current_app.config.get("TESTING"):
                return f(*args, **kwargs)

            # Determine client IP (handles standard X-Forwarded-For if behind proxy)
            client_ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
                request.remote_addr or
                "unknown"
            )

            now = time.time()
            window_start = now - 60.0

            with _lock:
                timestamps = _ip_buckets.setdefault(client_ip, [])
                # Prune timestamps older than 60s
                _ip_buckets[client_ip] = [t for t in timestamps if t > window_start]

                if len(_ip_buckets[client_ip]) >= requests_per_minute:
                    retry_after = int(60.0 - (now - _ip_buckets[client_ip][0])) + 1
                    resp, status = api_response(
                        success=False,
                        error=f"Too many requests. Rate limit of {requests_per_minute} requests per minute exceeded.",
                        status_code=429
                    )
                    resp.headers["Retry-After"] = str(max(1, retry_after))
                    return resp, status

                _ip_buckets[client_ip].append(now)

            return f(*args, **kwargs)
        return wrapped
    return decorator


def clear_rate_limits():
    """Clear in-memory buckets (useful for tests)."""
    with _lock:
        _ip_buckets.clear()
