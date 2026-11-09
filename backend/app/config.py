from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MISTRAL_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    DEFAULT_PROVIDER: str = "nvidia"

    MISTRAL_STRONG_MODEL: str = "mistral-large-latest"
    MISTRAL_CHEAP_MODEL: str = "mistral-small-latest"
    NVIDIA_STRONG_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b"
    NVIDIA_CHEAP_MODEL: str = "nvidia/nemotron-3.5-bolt-e4b"

    FERNET_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    DATABASE_URL: str = "sqlite:///./data/job_agent.db"
    BROWSER_PROFILE_DIR: str = "./data/browser_profile"
    LOG_LEVEL: str = "INFO"

    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000

    model_config = {
        "env_file": ["../.env", ".env"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_fernet() -> Optional[Fernet]:
    """Return a Fernet instance from the configured key, or None if unavailable."""
    key = get_settings().FERNET_KEY
    if not key:
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, Exception):
        return None


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string using the configured Fernet key."""
    f = get_fernet()
    if f is None:
        raise RuntimeError("Fernet key is not configured or is invalid")
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a ciphertext string using the configured Fernet key."""
    f = get_fernet()
    if f is None:
        raise RuntimeError("Fernet key is not configured or is invalid")
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Invalid ciphertext or wrong Fernet key")
