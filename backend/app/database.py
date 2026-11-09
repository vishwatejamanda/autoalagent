import os
from typing import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

# Ensure the data directory exists
_db_url = settings.DATABASE_URL
if _db_url.startswith("sqlite:///./"):
    _data_dir = os.path.dirname(_db_url.replace("sqlite:///./", "./"))
    os.makedirs(_data_dir, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


# Enable WAL mode and foreign keys for SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db() -> None:
    """Create all tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLModel session for use with FastAPI Depends."""
    with Session(engine) as session:
        yield session
