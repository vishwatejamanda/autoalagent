"""LinkedIn Job Source Adapter: uses persistent Playwright browser session."""

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
                return json.load(f).get("linkedin", {})
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


class LinkedInSource(JobSourceAdapter):
    """LinkedIn search and scraping adapter using user's persistent profile."""

    source_name: str = "linkedin"

    async def search(self, profile: Profile, filters: Optional[dict] = None) -> List[Job]:
        """Search LinkedIn jobs across roles, cities, and countries with optional filter overrides."""
        filters = filters or {}
        settings = get_settings()
        selectors = load_selectors()

        # 1. Resolve target roles
        if filters.get("roles"):
            roles_to_search = _parse_list_or_str(filters["roles"])
        else:
            roles_to_search = _parse_list_or_str(profile.target_titles) or ["Software Engineer"]

        # 2. Resolve target cities
        if filters.get("cities"):
            cities = _parse_list_or_str(filters["cities"])
        else:
            cities = _parse_list_or_str(profile.cities)

        # 3. Resolve target countries
        if filters.get("country"):
            countries = [filters["country"].strip()]
        elif filters.get("countries"):
            countries = _parse_list_or_str(filters["countries"])
        else:
            countries = _parse_list_or_str(profile.countries)

        # Compile locations: combine cities and countries, defaulting to Remote if none
        locations_to_search = []
        if cities:
            for city in cities:
                if countries:
                    locations_to_search.append(f"{city}, {countries[0]}")
                else:
                    locations_to_search.append(city)
        elif countries:
            locations_to_search.extend(countries)
        else:
            locations_to_search = ["Remote"]

        roles = roles_to_search[:2] if roles_to_search else ["Software Engineer"]

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

                for role in roles:
                    for location in locations_to_search[:3]:  # search up to 3 target locations per run
                        params = {
                            "keywords": role,
                            "location": location,
                            "f_AL": "true",  # Easy Apply
                            "sortBy": "DD",  # Date posted
                        }
                        search_url = f"https://www.linkedin.com/jobs/search/?{urllib.parse.urlencode(params)}"
                        logger.info("Navigating to LinkedIn search (%s in %s): %s", role, location, search_url)

                        try:
                            await page.goto(search_url, timeout=25000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(2500)

                            card_sel = selectors.get("job_card", "li.jobs-search-results__list-item")
                            title_sel = selectors.get("job_title", ".job-card-list__title")
                            comp_sel = selectors.get("company", ".job-card-container__company-name")
                            loc_sel = selectors.get("location", ".job-card-container__metadata-item")
                            link_sel = selectors.get("job_link", "a.job-card-list__title")

                            cards = await page.query_selector_all(card_sel)
                            for card in cards[:8]:
                                try:
                                    title_el = await card.query_selector(title_sel)
                                    title = (await title_el.inner_text()).strip() if title_el else ""

                                    comp_el = await card.query_selector(comp_sel)
                                    comp = (await comp_el.inner_text()).strip() if comp_el else ""

                                    loc_el = await card.query_selector(loc_sel)
                                    loc = (await loc_el.inner_text()).strip() if loc_el else location

                                    link_el = await card.query_selector(link_sel)
                                    href = (await link_el.get_attribute("href")) if link_el else ""
                                    if href and not href.startswith("http"):
                                        href = f"https://www.linkedin.com{href}"

                                    ext_id = href.split("currentJobId=")[-1].split("&")[0] if "currentJobId=" in href else str(abs(hash(href)))
                                    if title and comp and ext_id not in seen_ext_ids:
                                        seen_ext_ids.add(ext_id)
                                        found_jobs.append(Job(
                                            source="linkedin",
                                            external_id=ext_id,
                                            title=title,
                                            company=comp,
                                            location=loc,
                                            url=href,
                                            description=f"{title} at {comp}. Location: {loc}",
                                            easy_apply=True,
                                            status="new",
                                        ))
                                except Exception as exc:
                                    logger.debug("Error parsing single LinkedIn card: %s", exc)
                        except Exception as exc:
                            logger.warning("LinkedIn search navigation error for (%s, %s): %s", role, location, exc)

                await context.close()
        except Exception as exc:
            logger.error("LinkedIn browser automation error: %s", exc)

        return found_jobs

    async def fetch_details(self, job: Job) -> Job:
        """Fetch full job description using Playwright persistent session."""
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

                desc_sel = selectors.get("job_description", ".jobs-description__content")
                desc_el = await page.query_selector(desc_sel)
                if desc_el:
                    job.description = (await desc_el.inner_text()).strip()
                    job.description_hash = compute_description_hash(job.description)

                await context.close()
        except Exception as exc:
            logger.warning("Error fetching LinkedIn job detail: %s", exc)

        return job
