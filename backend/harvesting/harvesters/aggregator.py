"""
AggregatorHarvester.

Harvests full-edition PDF newspapers from open aggregator portals such as DailyEpaper (dailyepaper.in).
Discovers daily Google Drive and direct PDF download links without requiring logins or subscriptions,
converting them into direct streaming downloads for the RMIA pipeline.
"""

import asyncio
import logging
import re
from datetime import date
from pathlib import Path
from typing import List, Optional

import httpx

from harvesting.core.base import BaseHarvester
from harvesting.core.models import EditionConfig, NewspaperSource
from harvesting.exceptions import EditionNotFound
from harvesting.utils import run_in_proactor_thread

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}


class AggregatorHarvester(BaseHarvester):
    """
    Harvests full-edition PDFs from aggregator websites.

    Strategy:
    1. Fetch the newspaper's aggregator page (fast HTTP GET, falling back to Playwright if needed).
    2. Extract Google Drive and direct PDF download links.
    3. Match target date in link context (e.g. '21 Sep 2026: Download Now') or select the latest daily edition.
    4. Convert Google Drive file URLs to direct download links (drive.usercontent.google.com).
    5. Download full PDF via streaming PDFDownloader.
    """

    async def discover_editions(
        self,
        source: NewspaperSource,
        target_date: date,
    ) -> List[EditionConfig]:
        if source.editions:
            return source.editions
        return [EditionConfig(edition_name="default", region=source.region)]

    async def discover_pdf(
        self,
        source: NewspaperSource,
        edition: EditionConfig,
        target_date: date,
    ) -> str:
        url = edition.url_template or source.url_template or source.website_url
        if not url:
            raise EditionNotFound(f"No website_url configured for aggregator source: {source.id}")

        html = ""

        # 1. Attempt fast HTTP fetch
        try:
            async with httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True, timeout=30.0) as client:
                resp = await client.get(url)
                if resp.status_code < 400:
                    html = resp.text
        except Exception as http_err:
            logger.debug(f"HTTP fetch failed for {url}, falling back to browser: {http_err}")

        # 2. Fall back to Playwright if HTTP failed or returned empty
        if not html:
            async def _pw_fetch():
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage"],
                    )
                    context = await browser.new_context(
                        user_agent=BROWSER_HEADERS["User-Agent"],
                        locale="en-IN",
                        timezone_id="Asia/Kolkata",
                    )
                    page = await context.new_page()
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await page.wait_for_timeout(2000)
                    content = await page.content()
                    await browser.close()
                    return content

            try:
                html = await run_in_proactor_thread(_pw_fetch)
            except Exception as pw_err:
                logger.warning(f"Playwright navigation failed for {url}: {pw_err}")

        if not html:
            raise EditionNotFound(f"Unable to load aggregator page for {source.id} at {url}")

        # 3. Find all Google Drive or direct PDF links with surrounding context
        pattern = re.compile(
            r'<a\s+[^>]*href=[\'"](https://drive\.google\.com/[^\'"]+|https://[^\'"]+\.pdf)[\'"][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        matches = pattern.findall(html)
        if not matches:
            raw_urls = re.findall(
                r'href=[\'"](https://drive\.google\.com/[^\'"]+|https://[^\'"]+\.pdf)[\'"]',
                html,
                re.IGNORECASE,
            )
            if raw_urls:
                matches = [(u, "") for u in raw_urls]

        if not matches:
            raise EditionNotFound(f"No downloadable PDF or Drive links found on aggregator page {url} for {source.id}")

        # 4. Target date matching
        day_str = str(target_date.day)
        day_pad = f"{target_date.day:02d}"
        month_short = target_date.strftime("%b").lower()
        month_long = target_date.strftime("%B").lower()

        selected_link: Optional[str] = None
        for link_url, link_text in matches:
            idx = html.find(link_url)
            window = html[max(0, idx - 200):idx + 200].lower()
            if (day_str in window or day_pad in window) and (month_short in window or month_long in window):
                selected_link = link_url
                logger.info(f"Aggregator matched target date {target_date} for {source.id}: {selected_link}")
                break

        # Fallback to the topmost link (which is the most recent daily upload on DailyEpaper)
        if not selected_link:
            selected_link = matches[0][0]
            logger.info(f"Aggregator using latest available daily edition for {source.id}: {selected_link}")

        # 5. Convert Google Drive link to direct download link
        if "drive.google.com" in selected_link:
            fid_match = re.search(r'/d/([a-zA-Z0-9_-]+)', selected_link) or re.search(r'id=([a-zA-Z0-9_-]+)', selected_link)
            if fid_match:
                fid = fid_match.group(1)
                direct_url = f"https://drive.usercontent.google.com/download?id={fid}&export=download"
                logger.debug(f"Converted Google Drive link to direct download: {direct_url}")
                return direct_url

        return selected_link
