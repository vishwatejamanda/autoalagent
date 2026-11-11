"""Naukri Job Source Adapter: uses persistent Playwright browser session."""

import json
import logging
import os
import urllib.parse
from typing import List, Optional
from playwright.async_api import async_playwright

from app.config import get_settings
from models.job import Job
from models.profile import Profile
from services.dedupe import compute_description_hash
from sources.base import JobSourceAdapter

logger = logging.getLogger(__name__)


def load_selectors() -> dict:
    sel_path = os.path.join(os.path.dirname(__file__), "selectors.json")
    if os.path.exists(sel_path):
        try:
            with open(sel_path, "r", encoding="utf-8") as f:
                return json.load(f).get("naukri", {})
        except Exception:
            pass
    return {}


def _parse_list_or_str(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            pass
        return [v.strip() for v in val.split(",") if v.strip()]
    return []


class NaukriSource(JobSourceAdapter):
    """Naukri.com search and scraping adapter."""

    source_name: str = "naukri"

    async def search(self, profile: Profile, filters: Optional[dict] = None) -> List[Job]:
        """Search Naukri for jobs across multiple roles and cities with optional filter overrides."""
        filters = filters or {}
        settings = get_settings()
        selectors = load_selectors()

        # 1. Resolve target roles
        if filters.get("roles"):
            target_titles = _parse_list_or_str(filters["roles"])
        else:
            target_titles = _parse_list_or_str(profile.target_titles) or ["software-engineer"]

        # 2. Resolve target cities
        if filters.get("cities"):
            cities = _parse_list_or_str(filters["cities"])
        elif filters.get("country"):
            cities = [filters["country"].strip()]
        else:
            cities = _parse_list_or_str(profile.cities) or ["india"]

        target_limit = int(filters.get("limit", 30) or 30)
        exp_val = profile.max_experience if profile.max_experience is not None else 0
        roles = [t.lower().replace(" ", "-") for t in target_titles[:5]] if target_titles else ["software-engineer"]
        search_locations = [c.lower().replace(" ", "-") for c in cities[:4]] if cities else ["india"]

        profile_dir = os.path.abspath(settings.BROWSER_PROFILE_DIR)
        os.makedirs(profile_dir, exist_ok=True)

        found_jobs: List[Job] = []
        seen_ext_ids = set()

        try:
            async with async_playwright() as p:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = await context.new_page()

                for role_slug in roles:
                    if len(found_jobs) >= target_limit:
                        break
                    for loc_slug in search_locations:
                        if len(found_jobs) >= target_limit:
                            break
                        search_slug = f"{role_slug}-jobs-in-{loc_slug}"
                        search_url = f"https://www.naukri.com/{search_slug}?experience={exp_val}"
                        logger.info("Navigating to Naukri search (%s in %s): %s", role_slug, loc_slug, search_url)

                        try:
                            await page.goto(search_url, timeout=25000, wait_until="domcontentloaded")
                            try:
                                await page.wait_for_selector("div.srp-jobtuple-wrapper, article.jobTuple", timeout=10000)
                            except Exception:
                                pass
                            await page.mouse.wheel(0, 1200)
                            await page.wait_for_timeout(1500)

                            card_sel = selectors.get("job_card", "div.srp-jobtuple-wrapper")
                            title_sel = selectors.get("job_title", "a.title")
                            comp_sel = selectors.get("company", "a.comp-name")
                            loc_sel = selectors.get("location", "span.locWdth")
                            desc_sel = selectors.get("description", "div.job-desc")

                            cards = await page.query_selector_all(f"{card_sel}, article.jobTuple")
                            for card in cards[:target_limit]:
                                try:
                                    title_el = await card.query_selector(title_sel)
                                    title = (await title_el.inner_text()).strip() if title_el else ""

                                    comp_el = await card.query_selector(comp_sel)
                                    comp = (await comp_el.inner_text()).strip() if comp_el else ""

                                    loc_el = await card.query_selector(loc_sel)
                                    loc = (await loc_el.inner_text()).strip() if loc_el else loc_slug

                                    desc_el = await card.query_selector(desc_sel)
                                    desc = (await desc_el.inner_text()).strip() if desc_el else f"{title} at {comp}"

                                    href = (await title_el.get_attribute("href")) if title_el else ""
                                    job_id_match = card.get_attribute("data-job-id")
                                    ext_id = (await job_id_match) if job_id_match else str(abs(hash(href or title + comp)))

                                    if title and comp and ext_id not in seen_ext_ids:
                                        seen_ext_ids.add(ext_id)
                                        found_jobs.append(Job(
                                            source="naukri",
                                            external_id=ext_id,
                                            title=title,
                                            company=comp,
                                            location=loc,
                                            url=href,
                                            description=desc,
                                            easy_apply=True,
                                            status="new",
                                            description_hash=compute_description_hash(desc),
                                        ))
                                except Exception as exc:
                                    logger.debug("Error parsing single Naukri card: %s", exc)
                        except Exception as exc:
                            logger.warning("Naukri search navigation error for (%s, %s): %s", role_slug, loc_slug, exc)

                await context.close()
        except Exception as exc:
            logger.error("Naukri browser automation error: %s", exc)

        return found_jobs

    async def fetch_details(self, job: Job) -> Job:
        """Fetch full description from Naukri job detail page."""
        if job.description and len(job.description) > 200:
            return job

        settings = get_settings()
        selectors = load_selectors()
        profile_dir = os.path.abspath(settings.BROWSER_PROFILE_DIR)

        try:
            async with async_playwright() as p:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = await context.new_page()
                await page.goto(job.url, timeout=25000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                desc_sel = selectors.get("job_description", "section.job-desc-curated")
                desc_el = await page.query_selector(desc_sel)
                if desc_el:
                    job.description = (await desc_el.inner_text()).strip()
                    job.description_hash = compute_description_hash(job.description)

                await context.close()
        except Exception as exc:
            logger.warning("Error fetching Naukri job detail: %s", exc)

        return job
