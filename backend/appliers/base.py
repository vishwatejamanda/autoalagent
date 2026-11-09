"""Base Applier class with human delays, CAPTCHA detection, and screenshot logging."""

import asyncio
import logging
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from playwright.async_api import Page, BrowserContext

from app.config import get_settings
from models.job import Job

logger = logging.getLogger(__name__)


class ApplyResult(BaseModel):
    success: bool
    status: str  # "submitted", "review_needed", "manual_needed", "failed", "captcha_blocked"
    screenshot_path: str = ""
    error_message: str = ""
    details: str = ""


class BaseApplier(ABC):
    """Abstract base applier with safety precautions and anti-detection mechanisms."""

    portal_name: str = ""

    async def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.5):
        """Inject human-like randomized typing and reading pauses."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def detect_captcha(self, page: Page) -> bool:
        """Check for known CAPTCHA elements (reCAPTCHA, Cloudflare, hCaptcha, Arkose)."""
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='challenges.cloudflare.com']",
            "div.g-recaptcha",
            "#captcha-internal",
            "div[data-automation-id='captcha']",
            "div#arkose-iframe",
        ]
        for sel in captcha_selectors:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                logger.warning("CAPTCHA detected via selector '%s' on %s!", sel, page.url)
                return True
        return False

    async def save_screenshot(self, page: Page, prefix: str = "applier") -> str:
        """Save screenshot to data/screenshots directory."""
        os.makedirs("./data/screenshots", exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        path = os.path.abspath(os.path.join("./data/screenshots", filename))
        try:
            await page.screenshot(path=path, full_page=False)
            return path
        except Exception as exc:
            logger.error("Failed capturing screenshot: %s", exc)
            return ""

    @abstractmethod
    async def apply(
        self,
        job: Job,
        resume_path: str,
        mode: str = "review",  # "off" | "review" | "auto"
    ) -> ApplyResult:
        """Execute the portal application flow."""
        ...

