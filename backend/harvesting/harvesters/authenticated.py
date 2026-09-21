"""
AuthenticatedPlaywrightHarvester.

Extends PlaywrightHarvester with persistent per-source session management.

Authentication flow:
    1. Check for saved browser storage state (auth/{source_id}.json)
    2. Restore state → navigate to site
    3. Detect if session is expired (redirected to login, or paywall)
    4. If expired → raise AuthRequired (do not attempt login automatically)
    5. If CAPTCHA → raise CaptchaRequired
    6. Proceed with PDF discovery as PlaywrightHarvester

Manual reauthentication:
    The /api/harvesting/sources/{id}/reauthenticate endpoint instructs
    an operator to run the manual auth helper which saves a new storage state.

Credentials are read from environment variables only — never hardcoded.
They are never logged.
"""

import logging
import os
from datetime import date
from pathlib import Path
from typing import List, Optional

from harvesting.core.models import EditionConfig, NewspaperSource
from harvesting.exceptions import AuthRequired, CaptchaRequired, EditionNotFound
from harvesting.harvesters.playwright import PlaywrightHarvester, _is_captcha_page
from harvesting.utils import substitute_date_in_url, run_in_proactor_thread

logger = logging.getLogger(__name__)

LOGIN_INDICATORS = [
    "login", "sign in", "signin", "log in",
    "password", "username", "email", "email address",
]
PAYWALL_INDICATORS = [
    "subscribe", "subscription required", "premium content",
    "access denied", "paywall",
]


def _is_login_page(content: str) -> bool:
    lower = content.lower()
    return sum(1 for ind in LOGIN_INDICATORS if ind in lower) >= 2


def _is_paywall_page(content: str) -> bool:
    lower = content.lower()
    return any(ind in lower for ind in PAYWALL_INDICATORS)


class AuthenticatedPlaywrightHarvester(PlaywrightHarvester):
    """
    Playwright harvester with session persistence and auth detection.

    Sessions are stored as Playwright browser storage state JSON files:
        storage/auth/{source_id}.json
    """

    def _get_auth_state_path(self, source: NewspaperSource) -> Path:
        from config import get_settings
        settings = get_settings()
        auth_dir = Path(settings.storage_path) / "auth"
        auth_dir.mkdir(parents=True, exist_ok=True)
        filename = source.auth_state_file or f"{source.id}.json"
        return auth_dir / filename

    def _get_credentials(self, source: NewspaperSource) -> dict:
        """
        Read credentials from environment variables.

        Convention: {PREFIX}_USERNAME, {PREFIX}_PASSWORD
        Prefix is defined in source.credentials_env_prefix (e.g. "THE_HINDU")
        Returns empty dict if not configured.
        Never logs values.
        """
        prefix = source.credentials_env_prefix
        if not prefix:
            return {}
        username = os.environ.get(f"{prefix}_USERNAME", "")
        password = os.environ.get(f"{prefix}_PASSWORD", "")
        return {"username": username, "password": password}

    async def discover_pdf(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
    ) -> str:
        """
        Attempt discovery with saved session; raise AuthRequired if expired.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright is not installed.")

        auth_state_path = self._get_auth_state_path(source)
        url_template = edition.url_template or source.url_template or source.website_url
        if not url_template:
            raise EditionNotFound(f"No URL for source: {source.id}")
        start_url = substitute_date_in_url(url_template, target_date)

        async def _do_session_discover():
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )

                # Restore session if available
                context_kwargs = {}
                if auth_state_path.exists():
                    context_kwargs["storage_state"] = str(auth_state_path)
                    logger.info(f"source={source.id} status=RESTORING_SESSION")
                else:
                    logger.info(f"source={source.id} status=NO_SESSION_FILE")

                context = await browser.new_context(
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                    **context_kwargs,
                )
                page = await context.new_page()

                discovered_url: Optional[str] = None

                async def handle_response(response):
                    nonlocal discovered_url
                    content_type = response.headers.get("content-type", "")
                    if "pdf" in content_type and discovered_url is None:
                        discovered_url = response.url

                page.on("response", handle_response)

                try:
                    await page.goto(start_url, wait_until="networkidle", timeout=60_000)
                    content = await page.content()

                    # Security checks
                    if _is_captcha_page(content):
                        raise CaptchaRequired(f"CAPTCHA detected: {source.id}")

                    if _is_login_page(content) or _is_paywall_page(content):
                        logger.warning(f"source={source.id} status=SESSION_EXPIRED")
                        raise AuthRequired(
                            f"Session expired or auth required for source: {source.id}. "
                            f"Delete {auth_state_path} and reauthenticate."
                        )

                    if discovered_url:
                        return discovered_url

                    # DOM scan (reuse parent logic via super)
                    from harvesting.harvesters.playwright import _looks_like_pdf_url
                    links = await page.eval_on_selector_all(
                        "a[href]",
                        """els => els.map(e => ({
                            href: e.href,
                            dataSrc: e.getAttribute('data-src') || e.getAttribute('data-href')
                        }))""",
                    )
                    for link in links:
                        href = link.get("href", "") or ""
                        if _looks_like_pdf_url(href):
                            return href
                        data_src = link.get("dataSrc", "") or ""
                        if data_src and _looks_like_pdf_url(data_src):
                            return data_src

                    raise EditionNotFound(
                        f"No PDF found on {start_url} for authenticated source {source.id}"
                    )

                finally:
                    await browser.close()

        return await run_in_proactor_thread(_do_session_discover)
