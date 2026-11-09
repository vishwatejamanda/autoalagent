"""Workday Multi-Step Application Engine."""

import json
import logging
import os
import re
from playwright.async_api import async_playwright
from sqlmodel import Session, select

from app.config import get_settings, decrypt_value
from models.job import Job
from models.settings import PortalAccount
from schemas.profile import MasterProfileData
from services.answer_bank import find_saved_answer, draft_and_record_answer
from appliers.base import BaseApplier, ApplyResult

logger = logging.getLogger(__name__)


class WorkdayApplier(BaseApplier):
    """Workday dynamic multi-page application filler based on data-automation-id."""

    portal_name: str = "workday"

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
                logger.info("Opening Workday posting: %s", job.url)
                await page.goto(job.url, timeout=40000, wait_until="domcontentloaded")
                await self.random_delay(2, 4)

                # Check CAPTCHA
                if await self.detect_captcha(page):
                    ss = await self.save_screenshot(page, "workday_captcha")
                    await context.close()
                    return ApplyResult(
                        success=False,
                        status="captcha_blocked",
                        screenshot_path=ss,
                        error_message="CAPTCHA challenge encountered on Workday.",
                    )

                # Click Apply button
                apply_button = await page.query_selector(
                    "a[data-automation-id='adventureButton'], button[data-automation-id='applyButton'], a[data-automation-id='applyManually']"
                )
                if not apply_button:
                    # Check if external link
                    ss = await self.save_screenshot(page, "workday_external")
                    await context.close()
                    return ApplyResult(
                        success=False,
                        status="manual_needed",
                        screenshot_path=ss,
                        details="No direct apply button found; likely redirects to external portal.",
                    )

                await apply_button.click()
                await self.random_delay(2, 4)

                # Step 1: Sign in / Create Account if prompted
                sign_in_header = await page.query_selector("div[data-automation-id='signInHeader'], h2:has-text('Sign In')")
                if sign_in_header:
                    # Look up credentials in PortalAccount table
                    match = re.search(r"https://([^.]+)", job.url)
                    tenant = match.group(1) if match else "workday"
                    account = self.session.exec(
                        select(PortalAccount).where(PortalAccount.portal == "workday").where(PortalAccount.tenant == tenant)
                    ).first()

                    if account and account.encrypted_password:
                        try:
                            pwd = decrypt_value(account.encrypted_password)
                            email_input = await page.query_selector("input[data-automation-id='email']")
                            pwd_input = await page.query_selector("input[data-automation-id='password']")
                            if email_input and pwd_input:
                                await email_input.fill(account.username)
                                await pwd_input.fill(pwd)
                                sign_in_btn = await page.query_selector("button[data-automation-id='signInSubmitButton']")
                                if sign_in_btn:
                                    await sign_in_btn.click()
                                    await self.random_delay(3, 5)
                        except Exception as e:
                            logger.error("Failed decrypting/filling Workday credentials: %s", e)
                    else:
                        ss = await self.save_screenshot(page, "workday_signin_required")
                        await context.close()
                        return ApplyResult(
                            success=False,
                            status="manual_needed",
                            screenshot_path=ss,
                            details=f"Sign-in required for Workday tenant '{tenant}' but no credentials configured in Settings.",
                        )

                # Step 2: Upload Resume
                upload_input = await page.query_selector("input[type='file'], input[data-automation-id='file-upload-input-ref']")
                if upload_input and os.path.exists(resume_path):
                    await upload_input.set_input_files(os.path.abspath(resume_path))
                    logger.info("Uploaded tailored resume to Workday: %s", resume_path)
                    await self.random_delay(2, 4)

                # Step 3: Fill contact / name fields
                first_name_input = await page.query_selector("input[data-automation-id='legalNameSection_firstName']")
                if first_name_input and self.master.contact.full_name:
                    names = self.master.contact.full_name.split()
                    await first_name_input.fill(names[0])
                    last_name_input = await page.query_selector("input[data-automation-id='legalNameSection_lastName']")
                    if last_name_input and len(names) > 1:
                        await last_name_input.fill(" ".join(names[1:]))

                phone_input = await page.query_selector("input[data-automation-id='phone-number']")
                if phone_input and self.master.contact.phone:
                    await phone_input.fill(self.master.contact.phone)

                # Step 4: Mode Handling
                ss = await self.save_screenshot(page, f"workday_{job.id}")

                if mode == "review":
                    await context.close()
                    return ApplyResult(
                        success=True,
                        status="review_needed",
                        screenshot_path=ss,
                        details="Form autofilled successfully. Ready for manual review and submission.",
                    )
                elif mode == "auto":
                    # Look for final submit button
                    submit_btn = await page.query_selector("button[data-automation-id='bottom-navigation-next-button']")
                    if submit_btn:
                        btn_text = (await submit_btn.inner_text()).lower()
                        if "submit" in btn_text:
                            await submit_btn.click()
                            await self.random_delay(3, 5)
                            final_ss = await self.save_screenshot(page, f"workday_submitted_{job.id}")
                            await context.close()
                            return ApplyResult(
                                success=True,
                                status="submitted",
                                screenshot_path=final_ss,
                                details="Application submitted automatically.",
                            )

                    await context.close()
                    return ApplyResult(
                        success=True,
                        status="review_needed",
                        screenshot_path=ss,
                        details="Filled initial steps; multi-page flow requires user confirmation.",
                    )

                await context.close()
                return ApplyResult(success=True, status="review_needed", screenshot_path=ss)

            except Exception as exc:
                logger.error("Exception in Workday application engine: %s", exc)
                ss = await self.save_screenshot(page, "workday_error")
                await context.close()
                return ApplyResult(
                    success=False,
                    status="failed",
                    screenshot_path=ss,
                    error_message=str(exc),
                )

