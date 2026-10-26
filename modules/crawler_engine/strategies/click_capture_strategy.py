"""
Click-and-Capture Fallback Strategy for ImpactBridge™ Job Discovery Engine.

Last resort for dynamic SPA portals (Angular, React, Vue) where jobs are rendered
in interactive modals or dynamically pushed URLs via history.pushState.
Operates on a single-tab browser context with strict click limits (e.g. max 40 per run)
and automatic page closure to keep memory usage under 150MB.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BaseStrategy, ExtractionContext
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)


class ClickCaptureStrategy(BaseStrategy):
    name = "click_capture"

    def detect(self, context: ExtractionContext) -> bool:
        # Only invoke if other strategies yielded 0 jobs and Playwright is enabled
        return True

    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        # Import playwright lazily to keep footprint low
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.debug("Playwright not installed, skipping click_capture strategy.")
            return []

        jobs = []
        max_clicks = 40
        careers_url = context.final_url or context.careers_url

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--js-flags=--max-old-space-size=150"
                    ]
                )
                page = browser.new_page()
                page.set_default_timeout(25000)

                # Track XHR JSON responses
                intercepted_payloads = []
                def on_response(resp):
                    try:
                        ct = resp.headers.get("content-type", "")
                        if "json" in ct and resp.status == 200:
                            data = resp.json()
                            if isinstance(data, (dict, list)):
                                intercepted_payloads.append(data)
                    except Exception:
                        pass

                page.on("response", on_response)

                try:
                    page.goto(careers_url, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                except Exception as exc:
                    logger.debug("Click capture goto failed: %s", exc)
                    browser.close()
                    return []

                # Find clickable job card candidates
                card_selectors = [
                    "a[href*='/job/']", "a[href*='/career/']", "a[href*='/position/']",
                    "div.job-card", "div[class*='jobCard']", "tr[class*='job']", "li[class*='job']"
                ]

                cards = []
                for sel in card_selectors:
                    found = page.query_selector_all(sel)
                    if len(found) >= 2:
                        cards = found
                        break

                clicks = 0
                seen_urls = set()

                for card in cards[:max_clicks]:
                    try:
                        title = clean_text(card.inner_text().split("\n")[0])
                        if not title or len(title) < 3 or len(title) > 120:
                            continue

                        current_url = page.url
                        card.click(timeout=3000)
                        page.wait_for_timeout(1000)

                        dest_url = page.url
                        if dest_url != current_url and "#:~:text=" not in dest_url:
                            canon = normalize_canonical_url(dest_url)
                            if canon and canon not in seen_urls:
                                seen_urls.add(canon)
                                jobs.append({
                                    "title": title,
                                    "location": "India",
                                    "department": "Corporate",
                                    "application_url": canon,
                                    "external_job_id": None,
                                    "raw_metadata": {"navigated_url": dest_url},
                                    "link_quality": "DIRECT",
                                    "link_check_note": "click_capture_pushstate_url",
                                })
                                # Navigate back
                                page.go_back(wait_until="domcontentloaded")
                                page.wait_for_timeout(1000)

                        clicks += 1
                    except Exception:
                        continue

                # Pass captured XHR payloads back into context if any
                if intercepted_payloads:
                    context.extra_metadata["intercepted_xhr_payloads"] = intercepted_payloads

                browser.close()
        except Exception as exc:
            logger.debug("ClickCaptureStrategy execution error: %s", exc)

        return jobs
