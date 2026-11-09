"""LinkedIn Easy Apply Multi-Step Form Filler."""

import logging
import os
from playwright.async_api import async_playwright
from sqlmodel import Session

from app.config import get_settings
from models.job import Job
from schemas.profile import MasterProfileData
from services.answer_bank import find_saved_answer, draft_and_record_answer
from appliers.base import BaseApplier, ApplyResult

logger = logging.getLogger(__name__)


class LinkedInApplier(BaseApplier):
    """Automates multi-step LinkedIn Easy Apply modal dialogs."""

    portal_name: str = "linkedin"

    def __init__(self, session: Session, master_data: MasterProfileData):
        self.session = session
        self.master = master_data

    async def apply(
        self,
        job: Job,
        resume_path: str,
        mode: str = "review",
    ) -> ApplyResult:
        settings = get_settings()
        profile_dir = os.path.abspath(settings.BROWSER_PROFILE_DIR)

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = await context.new_page()

            try:
                logger.info("Opening LinkedIn posting: %s", job.url)
                await page.goto(job.url, timeout=35000, wait_until="domcontentloaded")
                await self.random_delay(2, 4)

                # 1. CAPTCHA Check
                if await self.detect_captcha(page):
                    ss = await self.save_screenshot(page, "linkedin_captcha")
                    await context.close()
                    return ApplyResult(
                        success=False,
                        status="captcha_blocked",
                        screenshot_path=ss,
                        error_message="CAPTCHA challenge encountered on LinkedIn.",
                    )

                # 2. Find Easy Apply button
                apply_btn = await page.query_selector("button.jobs-apply-button")
                if not apply_btn:
                    ss = await self.save_screenshot(page, "linkedin_no_easy_apply")
                    await context.close()
                    return ApplyResult(
                        success=False,
                        status="manual_needed",
                        screenshot_path=ss,
                        details="No Easy Apply button found; this position requires external company website application.",
                    )

                await apply_btn.click()
                await self.random_delay(2, 3)

                # Multi-step dialog loop (max 7 steps)
                for step in range(7):
                    modal = await page.query_selector("div.jobs-easy-apply-modal")
                    if not modal:
                        break

                    # Check for resume upload input
                    upload_input = await modal.query_selector("input[type='file']")
                    if upload_input and os.path.exists(resume_path):
                        await upload_input.set_input_files(os.path.abspath(resume_path))
                        logger.info("Uploaded tailored resume to LinkedIn modal: %s", resume_path)
                        await self.random_delay(1.5, 3)

                    # Look for Next / Review button
                    next_btn = await modal.query_selector("button[aria-label*='Continue'], button[aria-label*='Review']")
                    submit_btn = await modal.query_selector("button[aria-label*='Submit application']")

                    if submit_btn:
                        # At final review step
                        ss = await self.save_screenshot(page, f"linkedin_preview_{job.id}")
                        if mode == "auto":
                            await submit_btn.click()
                            await self.random_delay(3, 5)
                            final_ss = await self.save_screenshot(page, f"linkedin_submitted_{job.id}")
                            await context.close()
                            return ApplyResult(
                                success=True,
                                status="submitted",
                                screenshot_path=final_ss,
                                details="Easy Apply submitted automatically.",
                            )
                        else:
                            await context.close()
                            return ApplyResult(
                                success=True,
                                status="review_needed",
                                screenshot_path=ss,
                                details="Filled all steps; paused for user confirmation before submitting.",
                            )

                    if next_btn:
                        await next_btn.click()
                        await self.random_delay(2, 3.5)
                    else:
                        break

                ss = await self.save_screenshot(page, f"linkedin_review_{job.id}")
                await context.close()
                return ApplyResult(
                    success=True,
                    status="review_needed",
                    screenshot_path=ss,
                    details="Completed automated form filling.",
                )

            except Exception as exc:
                logger.error("Exception in LinkedIn Easy Apply: %s", exc)
                ss = await self.save_screenshot(page, "linkedin_error")
                await context.close()
                return ApplyResult(
                    success=False,
                    status="failed",
                    screenshot_path=ss,
                    error_message=str(exc),
                )

