from datetime import datetime, timezone

from sqlmodel import Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp fields."""

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
