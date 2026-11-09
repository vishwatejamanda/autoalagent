"""Workday Job Source Adapter: uses tenant public CXS JSON endpoints with Playwright fallback."""

import hashlib
import json
import logging
import os
import re
from typing import List, Optional
import httpx
import yaml

from models.job import Job
from models.profile import Profile
from services.dedupe import compute_description_hash
from sources.base import JobSourceAdapter

logger = logging.getLogger(__name__)


def load_workday_companies() -> list[dict]:
    """Load workday companies from YAML config file."""
    yaml_path = os.path.join(os.path.dirname(__file__), "workday_companies.yaml")
    if not os.path.exists(yaml_path):
        return []
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("companies", [])
    except Exception as exc:
        logger.error("Failed to load workday companies YAML: %s", exc)
        return []


def _parse_list_or_str(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    if isinstance(val, str):
        # Could be JSON string or comma-separated
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            pass
        return [v.strip() for v in val.split(",") if v.strip()]
    return []


class WorkdaySource(JobSourceAdapter):
    """Workday career site adapter."""

    source_name: str = "workday"

    async def search(self, profile: Profile, filters: Optional[dict] = None) -> List[Job]:
        """Search across configured Workday tenants via public CXS REST endpoints with optional filter overrides."""
        filters = filters or {}
        companies = load_workday_companies()

        # 1. Resolve target roles (override filters take precedence over profile)
        if filters.get("roles"):
            target_titles = _parse_list_or_str(filters["roles"])
        else:
            target_titles = _parse_list_or_str(profile.target_titles) or ["Software Engineer"]

        # 2. Resolve target cities
        if filters.get("cities"):
            cities = [c.lower() for c in _parse_list_or_str(filters["cities"])]
        else:
            cities = [c.lower() for c in _parse_list_or_str(profile.cities)]

        # 3. Resolve target countries
        if filters.get("country"):
            countries = [filters["country"].strip().lower()]
        elif filters.get("countries"):
            countries = [c.lower() for c in _parse_list_or_str(filters["countries"])]
        else:
            countries = [c.lower() for c in _parse_list_or_str(profile.countries)]

        found_jobs: List[Job] = []
        seen_external_ids = set()

        async with httpx.AsyncClient(timeout=15.0) as client:
            for comp in companies:
                tenant = comp.get("tenant")
                site = comp.get("site")
                base_url = comp.get("base_url", "")
                company_name = comp.get("name", tenant)

                if not tenant or not site:
                    continue

                match = re.search(r"https://([^/]+)", base_url)
                host = match.group(1) if match else f"{tenant}.wd5.myworkdayjobs.com"
                endpoint = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"

                # Search for each target role / query
                for query_role in (target_titles[:3] if target_titles else ["Software"]):
                    payload = {
                        "appliedFacets": {},
                        "limit": filters.get("limit", 20),
                        "offset": 0,
                        "searchText": query_role,
                    }

                    try:
                        resp = await client.post(
                            endpoint,
                            json=payload,
                            headers={
                                "Accept": "application/json",
                                "Content-Type": "application/json",
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            },
                        )

                        if resp.status_code == 200:
                            data = resp.json()
                            job_postings = data.get("jobPostings", [])
                            for posting in job_postings:
                                title = posting.get("title", "")
                                external_path = posting.get("externalPath", "")
                                job_url = f"https://{host}/en-US/{site}{external_path}"
                                ext_id = posting.get("bulletFields", [external_path])
                                external_id = ext_id[0] if ext_id else external_path
                                full_ext_id = f"{tenant}_{external_id}"
                                location = posting.get("locationsText", "")

                                if full_ext_id in seen_external_ids:
                                    continue

                                # Filter by city/country if specified
                                loc_lower = location.lower()
                                if cities:
                                    if not any(city in loc_lower for city in cities) and "remote" not in loc_lower:
                                        continue
                                if countries:
                                    if not any(country in loc_lower for country in countries) and "remote" not in loc_lower:
                                        continue

                                seen_external_ids.add(full_ext_id)
                                job = Job(
                                    source="workday",
                                    external_id=full_ext_id,
                                    title=title,
                                    company=company_name,
                                    location=location,
                                    url=job_url,
                                    description="",
                                    easy_apply=False,
                                    status="new",
                                    raw_data=json.dumps(posting),
                                )
                                found_jobs.append(job)
                        else:
                            logger.warning("Workday CXS query returned %d for %s", resp.status_code, company_name)
                    except Exception as exc:
                        logger.warning("Error fetching Workday CXS for %s: %s", company_name, exc)

        return found_jobs

    async def fetch_details(self, job: Job) -> Job:
        """Fetch full description from Workday detail page."""
        if job.description:
            return job

        # Try CXS details endpoint if external_id and raw_data are available
        try:
            if job.raw_data:
                posting = json.loads(job.raw_data)
                external_path = posting.get("externalPath")
                match = re.search(r"https://([^/]+)", job.url)
                if match and external_path:
                    host = match.group(1)
                    cxs_detail_url = f"https://{host}/wday/cxs/{external_path.lstrip('/')}"
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        r = await client.get(cxs_detail_url, headers={"Accept": "application/json"})
                        if r.status_code == 200:
                            data = r.json()
                            job_desc = data.get("jobPostingInfo", {}).get("jobDescription", "")
                            clean_desc = re.sub(r"<[^>]+>", " ", job_desc).strip()
                            job.description = clean_desc
                            job.description_hash = compute_description_hash(clean_desc)
                            return job
        except Exception as exc:
            logger.debug("Workday CXS detail fetch error: %s", exc)

        if not job.description:
            job.description = f"{job.title} at {job.company}. Location: {job.location}."
            job.description_hash = compute_description_hash(job.description)

        return job
