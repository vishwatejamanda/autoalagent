"""Naukri Application Flow Handler."""

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


class NaukriApplier(BaseApplier):
    """Automates Naukri 1-click apply and questionnaire flows."""

    portal_name: str = "naukri"

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
                logger.info("Opening Naukri job URL: %s", job.url)
                await page.goto(job.url, timeout=35000, wait_until="domcontentloaded")
                await self.random_delay(2, 4)

                # 1. CAPTCHA Check
                if await self.detect_captcha(page):
                    ss = await self.save_screenshot(page, "naukri_captcha")
                    await context.close()
                    return ApplyResult(
                        success=False,
                        status="captcha_blocked",
                        screenshot_path=ss,
                        error_message="CAPTCHA challenge encountered on Naukri.",
                    )

                # 1b. Check if user is logged out (Continue with Google / Login gate)
                try:
                    await page.wait_for_selector(
                        "button#apply-button, button.apply-button, button.company-site-button, button:has-text('Continue with Google'), button:has-text('Login to apply'), a:has-text('Login')",
                        timeout=10000,
                    )
                except Exception:
                    pass

                login_gate = await page.query_selector(
                    "button:has-text('Continue with Google'), button:has-text('Login to apply'), a#login_Layer"
                )
                apply_btn = await page.query_selector("button#apply-button, button.apply-button")

                if login_gate and not apply_btn:
                    ss = await self.save_screenshot(page, "naukri_login_required")
                    await context.close()
                    return ApplyResult(
                        success=False,
                        status="login_required",
                        screenshot_path=ss,
                        error_message="Naukri sign-in required ('Continue with Google' / Login gate shown). Open Settings -> Browser Login -> Naukri to sign in once.",
                        details="Naukri session is not authenticated in Playwright browser profile.",
                    )

                # 2. Click Apply button
                if not apply_btn:
                    # Check if external redirect
                    ext_btn = await page.query_selector("button.company-site-button")
                    ss = await self.save_screenshot(page, "naukri_external")
                    await context.close()
                    return ApplyResult(
                        success=False,
                        status="manual_needed",
                        screenshot_path=ss,
                        details="Requires application on company careers site." if ext_btn else "Apply button not found (may require login or posting closed).",
                    )

                btn_text = (await apply_btn.inner_text()).lower()
                if "already applied" in btn_text:
                    await context.close()
                    return ApplyResult(
                        success=True,
                        status="submitted",
                        details="Already applied on Naukri.",
                    )

                await apply_btn.click()
                await self.random_delay(2, 4)

                # 3. Handle chatbot / questionnaire modal if Naukri prompts custom questions
                chatbot_inputs = await page.query_selector_all("div.chatbot_Drawer input[type='text'], div.chatbot_Drawer textarea")
                if chatbot_inputs:
                    from services.answer_bank import find_saved_answer, draft_and_record_answer
                    for inp in chatbot_inputs[:5]:
                        try:
                            q_label_el = await page.query_selector("div.chatbot_Drawer .botMsg:last-of-type")
                            q_text = (await q_label_el.inner_text()).strip() if q_label_el else "Application question"
                            saved_ans, is_approved = find_saved_answer(self.session, q_text)
                            if saved_ans and is_approved:
                                await inp.fill(saved_ans)
                            else:
                                ans, req_approval = await draft_and_record_answer(
                                    self.session, q_text, self.master, job_title=job.title, company=job.company
                                )
                                if not req_approval:
                                    await inp.fill(ans)
                        except Exception:
                            pass

                ss = await self.save_screenshot(page, f"naukri_preview_{job.id}")
                await context.close()
                return ApplyResult(
                    success=True,
                    status="review_needed" if mode == "review" else "submitted",
                    screenshot_path=ss,
                    details="Naukri 1-click apply triggered.",
                )

            except Exception as exc:
                logger.error("Exception in Naukri application flow: %s", exc)
                ss = await self.save_screenshot(page, "naukri_error")
                await context.close()
                return ApplyResult(
                    success=False,
                    status="failed",
                    screenshot_path=ss,
                    error_message=str(exc),
                )

