"""
Streaming PDF downloader with retry, backoff, timeout, and atomic rename.

Used by all harvester strategies to safely download PDF files.
"""

import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx

from harvesting.exceptions import DownloadFailed, EmptyFile, HarvestTimeout

logger = logging.getLogger(__name__)

# Limits
MIN_PDF_BYTES = 1_024           # 1 KB minimum
MAX_PDF_BYTES = 500_000_000     # 500 MB maximum
DEFAULT_TIMEOUT = 120           # seconds
DEFAULT_RETRIES = 3
BACKOFF_BASE = 2.0              # exponential backoff base (seconds)

# HTTP headers to appear like a browser
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
}


class PDFDownloader:
    """
    Downloads a PDF from a URL to a destination path.

    Features:
    - Streaming download (low memory)
    - Configurable timeout and retries
    - Exponential backoff between retries
    - Atomic rename (write to temp file first)
    - Maximum file-size guard
    - Partial download rejection
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_RETRIES,
        extra_headers: Optional[dict] = None,
    ):
        self._timeout = timeout
        self._max_retries = max_retries
        self._headers = {**BROWSER_HEADERS, **(extra_headers or {})}

    async def download(self, url: str, dest_path: Path) -> int:
        """
        Download URL to dest_path atomically.

        Returns:
            File size in bytes.

        Raises:
            DownloadFailed, EmptyFile, HarvestTimeout
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        last_error: Exception = DownloadFailed("Unknown error")

        for attempt in range(1, self._max_retries + 1):
            try:
                size = await self._attempt_download(url, dest_path)
                return size
            except HarvestTimeout as e:
                last_error = e
                logger.warning(f"Timeout (attempt {attempt}/{self._max_retries}): {url}")
            except DownloadFailed as e:
                last_error = e
                logger.warning(f"Download failed (attempt {attempt}/{self._max_retries}): {e}")
                if "HTTP 404" in str(e) or "HTTP 403" in str(e):
                    break
            except Exception as e:
                last_error = DownloadFailed(str(e))
                logger.warning(f"Unexpected error (attempt {attempt}/{self._max_retries}): {e}")

            if attempt < self._max_retries:
                backoff = BACKOFF_BASE ** attempt
                logger.info(f"Retrying in {backoff:.1f}s...")
                await asyncio.sleep(backoff)

        raise last_error

    async def _attempt_download(self, url: str, dest_path: Path) -> int:
        """Single download attempt with streaming and atomic rename."""
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp",
            dir=dest_path.parent,
        )
        try:
            async with httpx.AsyncClient(
                headers=self._headers,
                follow_redirects=True,
                timeout=httpx.Timeout(self._timeout),
            ) as client:
                try:
                    async with client.stream("GET", url) as response:
                        if response.status_code >= 400:
                            raise DownloadFailed(
                                f"HTTP {response.status_code} for {url}"
                            )

                        total = 0
                        with os.fdopen(tmp_fd, "wb") as f:
                            tmp_fd = -1  # fd transferred to file object
                            async for chunk in response.aiter_bytes(65536):
                                f.write(chunk)
                                total += len(chunk)
                                if total > MAX_PDF_BYTES:
                                    raise DownloadFailed(
                                        f"File exceeds maximum size "
                                        f"({MAX_PDF_BYTES // 1_000_000} MB): {url}"
                                    )

                except httpx.TimeoutException as e:
                    raise HarvestTimeout(f"Timeout downloading {url}: {e}")
                except httpx.RequestError as e:
                    raise DownloadFailed(f"Connection error for {url}: {e}")

            if total < MIN_PDF_BYTES:
                raise EmptyFile(f"File too small ({total} bytes): {url}")

            # Atomic rename
            os.replace(tmp_path, dest_path)
            tmp_path = None
            logger.info(f"Downloaded {total:,} bytes → {dest_path}")
            return total

        finally:
            # Clean up temp file on failure
            if tmp_fd != -1:
                try:
                    os.close(tmp_fd)
                except Exception:
                    pass
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
