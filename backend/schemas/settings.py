from typing import List, Optional

from pydantic import BaseModel


class SettingUpdate(BaseModel):
    value: str
    category: str = "general"


class SettingResponse(BaseModel):
    id: int
    key: str
    value: str
    category: str = "general"


class LLMProviderConfig(BaseModel):
    provider: str  # mistral / nvidia
    api_key: str = ""  # masked in responses (e.g. "sk-***abc")
    strong_model: str = ""
    cheap_model: str = ""


class AppSettings(BaseModel):
    """All settings grouped together for the Settings page."""

    default_provider: str = "mistral"
    llm_providers: List[LLMProviderConfig] = []
    telegram_bot_token: str = ""  # masked
    telegram_chat_id: str = ""
    database_url: str = ""
    browser_profile_dir: str = ""
    log_level: str = "INFO"
    backend_port: int = 8000
    frontend_port: int = 3000
    fernet_key_set: bool = False  # whether a key is configured (never expose raw key)
