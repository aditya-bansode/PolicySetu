"""
PolicySetu — Document Storage Manager
=====================================
Handles organized, content-addressable local document storage for downloaded
government policy documents (PDF, HTML). Prevents unnecessary duplicate file storage
via SHA-256 deduplication.

Security Guarantees:
- Path traversal defense: validates all paths strictly within base storage directory.
- File type restriction: only permitted document formats (PDF, HTML, text).
- File size limit: enforces 25MB maximum document buffer limit.
"""

import os
import hashlib
import mimetypes
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("policysetu.storage")

# Maximum permitted file size: 25 MB
MAX_DOCUMENT_SIZE_BYTES = 25 * 1024 * 1024

# Strictly permitted extensions
ALLOWED_EXTENSIONS = {".pdf", ".html", ".htm", ".txt", ".json"}


class DocumentStorageManager:
    """
    Manages local document file storage with content-addressable deduplication
    and strict path traversal & file size guardrails.
    """

    def __init__(self, base_storage_dir: Optional[str] = None, base_dir: Optional[str] = None):
        storage_path = base_dir or base_storage_dir or os.environ.get("DOCUMENT_STORAGE_DIR") or os.path.join("data", "documents", "storage")
        self.base_dir = os.path.abspath(storage_path)
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except OSError:
            import tempfile
            self.base_dir = os.path.join(tempfile.gettempdir(), "policysetu_docs")
            try:
                os.makedirs(self.base_dir, exist_ok=True)
            except OSError:
                pass

    @staticmethod
    def compute_sha256(content_bytes: bytes) -> str:
        """Compute SHA-256 hash string for raw byte stream."""
        return hashlib.sha256(content_bytes).hexdigest()

    def _determine_extension(self, content_bytes: bytes, filename_hint: str) -> str:
        """Determine file extension from magic bytes or hint, enforcing allowlist."""
        # Sanitize hint
        clean_hint = os.path.basename(filename_hint).replace("\x00", "")
        ext = os.path.splitext(clean_hint)[1].lower()

        if content_bytes.startswith(b"%PDF"):
            return ".pdf"
        elif (
            content_bytes.strip().startswith(b"<!DOCTYPE") or
            content_bytes.strip().startswith(b"<html") or
            content_bytes.strip().startswith(b"<?xml")
        ):
            return ".html"

        if ext in ALLOWED_EXTENSIONS:
            return ext
        return ".pdf"  # default to pdf for official government policy records

    def _is_safe_path(self, path: str) -> bool:
        """Verify path is contained strictly within the base storage directory."""
        try:
            abs_base = os.path.abspath(self.base_dir)
            abs_target = os.path.abspath(path)
            # Use os.path.commonpath to prevent prefix confusion
            return os.path.commonpath([abs_base, abs_target]) == abs_base
        except Exception:
            return False

    def save_document(
        self,
        content_bytes: bytes,
        filename_hint: str = "document.pdf",
        source_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Save document bytes into organized content-addressable directory.
        If a file with identical SHA-256 hash exists, avoids writing duplicate files.
        Enforces size and extension limits.
        """
        if not content_bytes:
            raise ValueError("Cannot save empty document byte buffer.")

        file_size = len(content_bytes)
        if file_size > MAX_DOCUMENT_SIZE_BYTES:
            raise ValueError(f"File size ({file_size} bytes) exceeds maximum permitted limit of {MAX_DOCUMENT_SIZE_BYTES} bytes (25MB).")

        content_hash = self.compute_sha256(content_bytes)
        ext = self._determine_extension(content_bytes, filename_hint)

        # Sanitize source_id directory
        clean_source = str(int(source_id)) if source_id is not None and str(source_id).isdigit() else "general"

        # Organized subdirectories: base_dir / <source_id or 'general'> / <hash_prefix> /
        subdir = os.path.join(self.base_dir, clean_source, content_hash[:2])
        os.makedirs(subdir, exist_ok=True)

        target_file_path = os.path.join(subdir, f"{content_hash}{ext}")

        # Path traversal guardrail
        if not self._is_safe_path(target_file_path):
            raise PermissionError("Unsafe target file path detected. Storage path escapes base directory.")

        # Deduplication check: Do not store duplicate files
        if os.path.exists(target_file_path):
            existing_size = os.path.getsize(target_file_path)
            logger.debug(f"[Storage] Deduplication hit: {target_file_path} already exists ({existing_size} bytes).")
            return {
                "file_path": target_file_path,
                "content_hash": content_hash,
                "file_size": existing_size,
                "is_duplicate": True,
                "mime_type": mimetypes.guess_type(target_file_path)[0] or "application/octet-stream",
            }

        # Atomically write file
        temp_path = f"{target_file_path}.tmp_{os.getpid()}"
        with open(temp_path, "wb") as f:
            f.write(content_bytes)
        os.replace(temp_path, target_file_path)

        logger.info(f"[Storage] Saved document ({file_size} bytes, SHA-256: {content_hash[:12]}...) to {target_file_path}")

        return {
            "file_path": target_file_path,
            "content_hash": content_hash,
            "file_size": file_size,
            "is_duplicate": False,
            "mime_type": mimetypes.guess_type(target_file_path)[0] or "application/octet-stream",
        }

    def read_document_bytes(self, file_path: str) -> Optional[bytes]:
        """Read and return document bytes from storage path with path traversal defense."""
        if not file_path or not self._is_safe_path(file_path) or not os.path.exists(file_path):
            return None
        with open(file_path, "rb") as f:
            return f.read()

    def get_document_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored file metadata with path traversal defense."""
        if not file_path or not self._is_safe_path(file_path) or not os.path.exists(file_path):
            return None
        size = os.path.getsize(file_path)
        mime, _ = mimetypes.guess_type(file_path)
        return {
            "file_path": file_path,
            "file_size": size,
            "mime_type": mime or "application/octet-stream",
            "exists": True,
        }
