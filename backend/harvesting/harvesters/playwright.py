"""
PlaywrightHarvester.

For JavaScript-rendered newspaper websites where the PDF URL cannot
be determined from a simple template.

Discovery strategy (language-independent, DOM-first):
    1. Open website URL in headless browser
    2. Navigate to today's edition (date-aware)
    3. Find downloadable PDF by:
        a. <a> with download attribute ending in .pdf
        b. <a href> ending in .pdf
        c. URL patterns matching /pdf/, /epaper/, /download/
        d. Configured CSS selectors (from source.selectors)
        e. data-* attributes
    4. Intercept PDF response headers via network events
    5. Download discovered URL via PDFDownloader
"""

import asyncio
import concurrent.futures
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from harvesting.core.base import BaseHarvester
from harvesting.core.models import EditionConfig, NewspaperSource
from harvesting.core.validator import ValidationStatus
from harvesting.exceptions import (
    EditionNotFound,
    AuthRequired,
    CaptchaRequired,
    EmptyFile,
    InvalidPDF,
    Duplicate,
)
from harvesting.utils import (
    calculate_sha256,
    make_newspaper_storage_path,
    substitute_date_in_url,
)

logger = logging.getLogger(__name__)

# Patterns that typically indicate a PDF link
PDF_URL_PATTERNS = [
    re.compile(r"\.pdf($|\?)", re.IGNORECASE),
    re.compile(r"/download.*\.pdf", re.IGNORECASE),
    re.compile(r"/pdf/", re.IGNORECASE),
    re.compile(r"[?&]format=pdf", re.IGNORECASE),
    re.compile(r"[?&]type=pdf", re.IGNORECASE),
]

# CAPTCHA signals
CAPTCHA_INDICATORS = [
    "captcha", "recaptcha", "hcaptcha", "are you human",
    "verify you are", "bot check",
]

# URL patterns that indicate the browser landed on a non-ePaper redirect
# (login, error, FAQ, etc.) — we should NOT attempt to render these as PDFs
REDIRECT_PAGE_URL_PATTERNS = [
    re.compile(r"/faq\.php", re.IGNORECASE),
    re.compile(r"/login", re.IGNORECASE),
    re.compile(r"/signin", re.IGNORECASE),
    re.compile(r"/error", re.IGNORECASE),
    re.compile(r"/404", re.IGNORECASE),
    re.compile(r"/subscribe", re.IGNORECASE),
    re.compile(r"/paywall", re.IGNORECASE),
]

REDIRECT_PAGE_CONTENT_SIGNALS = [
    "this page could not be found",
    "please subscribe to read",
    "subscription required to view",
    "please log in to continue",
    "you must be logged in",
]

REDIRECT_PAGE_TITLE_SIGNALS = [
    "page not found",
    "404",
    "access denied",
    "error",
    "login",
    "sign in",
]


def _is_redirect_page(url: str, content: str, start_url: Optional[str] = None) -> bool:
    """Return True if the browser has been redirected to an error, login, or non-ePaper page."""
    lower_url = url.lower()
    if any(p.search(lower_url) for p in REDIRECT_PAGE_URL_PATTERNS):
        return True

    # Check page <title> tag for explicit error / login / 404
    title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if title_match:
        title_text = title_match.group(1).lower().strip()
        if any(sig in title_text for sig in REDIRECT_PAGE_TITLE_SIGNALS):
            return True

    # Only inspect full body content signals if an actual URL redirect took place
    if start_url and lower_url.rstrip("/") != start_url.lower().rstrip("/"):
        lower_content = content.lower()
        return any(sig in lower_content for sig in REDIRECT_PAGE_CONTENT_SIGNALS)

    return False



def _looks_like_pdf_url(url: str) -> bool:
    return any(p.search(url) for p in PDF_URL_PATTERNS)


def _is_captcha_page(content: str) -> bool:
    lower = content.lower()
    return any(ind in lower for ind in CAPTCHA_INDICATORS)


def _loop_supports_subprocess() -> bool:
    """Check if the current running event loop supports subprocess execution."""
    try:
        loop = asyncio.get_running_loop()
        return type(loop).__name__ != "_WindowsSelectorEventLoop"
    except Exception:
        return False


def _run_in_proactor_thread(coro_fn, *args, **kwargs):
    """
    Run an async coroutine in a separate thread with WindowsProactorEventLoopPolicy.
    Ensures Playwright subprocess execution works on Windows even when uvicorn
    runs with SelectorEventLoop (e.g. during --reload).
    """
    def _worker():
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_fn(*args, **kwargs))
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_worker).result()


class PlaywrightHarvester(BaseHarvester):
    """
    Browser-based harvester using Playwright.

    Uses DOM-attribute discovery rather than hardcoded button text
    to remain language-independent.
    """

    async def discover_editions(
        self,
        source: NewspaperSource,
        target_date: date,
    ) -> List[EditionConfig]:
        """Return configured editions, or a single default if none listed."""
        if source.editions:
            return source.editions
        return [EditionConfig(edition_name="default", region=source.region)]

    async def discover_pdf(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
    ) -> str:
        """
        Open the source website in a headless browser and discover the PDF URL.
        Dispatches to a ProactorEventLoop thread on Windows if the running loop
        is SelectorEventLoop (such as under uvicorn --reload).
        """
        if not _loop_supports_subprocess():
            return await asyncio.to_thread(
                _run_in_proactor_thread,
                self._discover_pdf_impl,
                source,
                edition,
                target_date,
            )
        return await self._discover_pdf_impl(source, edition, target_date)

    async def _discover_pdf_impl(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
    ) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. "
                "Run: pip install playwright && playwright install chromium"
            )

        url_template = edition.url_template or source.url_template or source.website_url
        if not url_template:
            raise EditionNotFound(
                f"No website_url or url_template for source: {source.id}"
            )
        start_url = substitute_date_in_url(url_template, target_date)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-IN",
                timezone_id="Asia/Kolkata",
            )
            page = await context.new_page()

            discovered_url: Optional[str] = None

            # Intercept responses for PDF content
            async def handle_response(response):
                nonlocal discovered_url
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type and discovered_url is None:
                    discovered_url = response.url
                    logger.debug(f"PDF found via response intercept: {discovered_url}")

            page.on("response", handle_response)

                response = None
                try:
                    response = await page.goto(start_url, wait_until="domcontentloaded", timeout=25_000)
                    await page.wait_for_timeout(2000)
                except Exception as nav_err:
                    err_str = str(nav_err).lower()
                    if any(fatal in err_str for fatal in [
                        "err_name_not_resolved",
                        "err_connection_refused",
                        "err_connection_reset",
                        "err_timed_out",
                        "err_internet_disconnected",
                        "err_address_unreachable",
                    ]):
                        raise EditionNotFound(
                            f"Host unreachable for source {source.id} at {start_url}: {nav_err}"
                        )
                    logger.warning(f"Navigation warning on {start_url}: {nav_err}")

                if response and response.status in (404, 403, 410, 500, 502, 503):
                    raise EditionNotFound(
                        f"HTTP {response.status} returned for source {source.id} at {start_url}"
                    )

                try:
                    content = await page.content()
                except Exception as content_err:
                    logger.warning(f"Unable to read page content for {start_url}: {content_err}")
                    raise EditionNotFound(
                        f"Page content unavailable for source {source.id} at {start_url}: {content_err}"
                    )

                current_url = page.url

                if _is_captcha_page(content):
                    raise CaptchaRequired(
                        f"CAPTCHA detected on {source.id} at {start_url}"
                    )

                # Check for non-ePaper redirects (FAQ, login, error pages)
                if _is_redirect_page(current_url, content, start_url=start_url):
                    raise EditionNotFound(
                        f"Redirected to non-ePaper page ({current_url}) for source {source.id}. "
                        f"The site may require login or changed its URL structure."
                    )

                if discovered_url:
                    await browser.close()
                    return discovered_url

                # Use configured CSS selector first (if provided)
                custom_selector = (source.selectors or {}).get("pdf_link")
                if custom_selector:
                    try:
                        element = await page.wait_for_selector(
                            custom_selector, timeout=5_000
                        )
                        if element:
                            href = await element.get_attribute("href")
                            if href and _looks_like_pdf_url(href):
                                discovered_url = href
                    except Exception:
                        pass

                # DOM scan: look for PDF links
                if not discovered_url:
                    links = await page.eval_on_selector_all(
                        "a[href]",
                        """els => els.map(e => ({
                            href: e.href,
                            download: e.getAttribute('download'),
                            dataSrc: e.getAttribute('data-src') || e.getAttribute('data-href')
                        }))""",
                    )
                    for link in links:
                        href = link.get("href", "") or ""
                        if _looks_like_pdf_url(href):
                            discovered_url = href
                            break
                        # Check data attributes
                        data_src = link.get("dataSrc", "") or ""
                        if data_src and _looks_like_pdf_url(data_src):
                            discovered_url = data_src
                            break

                if not discovered_url:
                    raise EditionNotFound(
                        f"No direct PDF link found on {start_url} for source {source.id}"
                    )

                return discovered_url

            finally:
                await browser.close()

    async def download_edition(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
        storage: "HarvestStorage",  # type: ignore
    ) -> Tuple[Path, str]:
        """
        Full pipeline for one edition:
        1. Attempt discovery of direct PDF link & download.
        2. If direct PDF link is not present (e.g. dynamic web ePaper viewer),
           render the ePaper page directly to a broadsheet A3 PDF using Playwright.
        Dispatches to a ProactorEventLoop thread on Windows if running under SelectorEventLoop.
        """
        if not _loop_supports_subprocess():
            return await asyncio.to_thread(
                _run_in_proactor_thread,
                self._download_edition_impl,
                source,
                edition,
                target_date,
                storage,
            )
        return await self._download_edition_impl(source, edition, target_date, storage)

    async def _download_edition_impl(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
        storage: "HarvestStorage",  # type: ignore
    ) -> Tuple[Path, str]:
        try:
            return await super().download_edition(source, edition, target_date, storage)
        except EditionNotFound as enf:
            err_msg = str(enf).lower()
            # Do NOT attempt fallback PDF rendering if the site was unreachable, redirected to login/error, or has no content
            if any(skip in err_msg for skip in [
                "redirected to non-epaper page",
                "host unreachable",
                "page content unavailable",
                "cannot reach",
            ]):
                raise enf

            logger.info(
                f"Direct PDF link not found for {source.id}/{edition.edition_name}. "
                f"Attempting Playwright broadsheet PDF rendering fallback..."
            )
            dest_path = make_newspaper_storage_path(
                self._storage_root, source.id, target_date, edition.edition_name
            )
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            url_template = edition.url_template or source.url_template or source.website_url
            if not url_template:
                raise enf
            start_url = substitute_date_in_url(url_template, target_date)

            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-blink-features=AutomationControlled",
                        ],
                    )
                    context = await browser.new_context(
                        viewport={"width": 1440, "height": 900},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        locale="en-IN",
                        timezone_id="Asia/Kolkata",
                    )
                    render_resp = None
                    try:
                        render_resp = await page.goto(start_url, wait_until="domcontentloaded", timeout=30_000)
                        await page.wait_for_timeout(3000)
                    except Exception as nav_err:
                        logger.warning(f"Fallback render navigation warning on {start_url}: {nav_err}")
                        raise enf

                    if render_resp and render_resp.status in (404, 403, 410, 500, 502, 503):
                        logger.warning(f"Playwright render aborted for {source.id}: HTTP {render_resp.status}")
                        raise enf

                    # Guard: check if browser was redirected to a non-ePaper page
                    render_url = page.url
                    try:
                        render_content = await page.content()
                    except Exception:
                        render_content = ""

                    if _is_redirect_page(render_url, render_content, start_url=start_url):
                        await browser.close()
                        logger.warning(
                            f"Playwright render aborted for {source.id}: "
                            f"redirected to non-ePaper page {render_url}"
                        )
                        raise enf

                    # Print to broadsheet A3 PDF
                    await page.pdf(
                        path=str(dest_path),
                        format="A3",
                        print_background=True,
                        margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
                    )
                    await browser.close()
            except Exception as render_err:
                logger.error(f"Playwright fallback PDF render failed for {source.id}: {render_err}")
                raise enf

            # Validate rendered PDF
            status = self._validator.validate(dest_path)
            if status == ValidationStatus.EMPTY_FILE:
                dest_path.unlink(missing_ok=True)
                raise EmptyFile(f"Rendered empty PDF: {start_url}")
            if status == ValidationStatus.INVALID_PDF:
                dest_path.unlink(missing_ok=True)
                raise InvalidPDF(f"Rendered invalid PDF: {start_url}")

            sha256 = calculate_sha256(dest_path)
            if storage.sha256_exists(sha256):
                dest_path.unlink(missing_ok=True)
                raise Duplicate(
                    f"PDF already downloaded (sha256={sha256}): {source.id}/{edition.edition_name}"
                )

            file_size = dest_path.stat().st_size
            logger.info(
                f"source={source.id} edition={edition.edition_name} "
                f"status=VALIDATED size={file_size:,} sha256={sha256} (via Playwright render)"
            )
            return dest_path, sha256
