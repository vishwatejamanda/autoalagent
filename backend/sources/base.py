"""Abstract base class for job portal source adapters."""

from abc import ABC, abstractmethod
from typing import List, Optional
from models.job import Job
from models.profile import Profile


class JobSourceAdapter(ABC):
    """Base interface for all portal search adapters."""

    source_name: str = ""

    @abstractmethod
    async def search(self, profile: Profile, filters: Optional[dict] = None) -> List[Job]:
        """Search the portal for jobs matching profile criteria and optional override filters."""
        ...

    @abstractmethod
    async def fetch_details(self, job: Job) -> Job:
        """Fetch full description and details for a specific job."""
        ...
