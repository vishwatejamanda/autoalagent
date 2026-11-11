"""Settings API endpoints."""

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import get_settings, encrypt_value, decrypt_value
from app.database import get_session
from models.settings import Setting, PortalAccount
from models.audit import AuditLog
from llm.skills.context_builder import DEFAULT_APPLICATION_DEFAULTS

router = APIRouter(prefix="/settings", tags=["settings"])


# ─── App Settings (key-value store) ──────────────────────────


@router.get("")
async def get_all_settings(session: Session = Depends(get_session)):
    """Get all settings grouped by category."""
    settings_db = session.exec(select(Setting)).all()
    grouped: dict[str, dict[str, str]] = {}
    for s in settings_db:
        grouped.setdefault(s.category, {})[s.key] = s.value

    # Merge with env-based settings (read-only display)
    env_settings = get_settings()
    result = {
        "env": {
            "DEFAULT_PROVIDER": env_settings.DEFAULT_PROVIDER,
            "MISTRAL_API_KEY": _mask(env_settings.MISTRAL_API_KEY),
            "NVIDIA_API_KEY": _mask(env_settings.NVIDIA_API_KEY),
            "MISTRAL_STRONG_MODEL": env_settings.MISTRAL_STRONG_MODEL,
            "MISTRAL_CHEAP_MODEL": env_settings.MISTRAL_CHEAP_MODEL,
            "NVIDIA_STRONG_MODEL": env_settings.NVIDIA_STRONG_MODEL,
            "NVIDIA_CHEAP_MODEL": env_settings.NVIDIA_CHEAP_MODEL,
            "TELEGRAM_BOT_TOKEN": _mask(env_settings.TELEGRAM_BOT_TOKEN),
            "TELEGRAM_CHAT_ID": env_settings.TELEGRAM_CHAT_ID,
            "FERNET_KEY": "configured" if env_settings.FERNET_KEY else "not_set",
            "DATABASE_URL": env_settings.DATABASE_URL,
            "LOG_LEVEL": env_settings.LOG_LEVEL,
        },
        "db": grouped,
    }
    return result


def load_application_defaults(session: Session) -> dict[str, Any]:
    """Load persisted Fresher / N/A & custom Q&A defaults merged with baseline defaults."""
    merged = dict(DEFAULT_APPLICATION_DEFAULTS)
    rows = session.exec(select(Setting).where(Setting.category == "application_defaults")).all()
    for row in rows:
        if row.value is not None and row.value != "":
            merged[row.key] = row.value
    return merged


@router.get("/application-defaults")
async def get_application_defaults(session: Session = Depends(get_session)):
    """Get Fresher / N/A / Experience / Previous Company / Skills defaults for matching & applying."""
    return load_application_defaults(session)


@router.put("/application-defaults")
async def update_application_defaults(
    body: dict[str, Any],
    session: Session = Depends(get_session),
):
    """Persist application form defaults (experience level, previous company, skills, CTC, notice period)."""
    allowed_keys = set(DEFAULT_APPLICATION_DEFAULTS.keys())
    updated: list[str] = []
    for k, v in body.items():
        if k not in allowed_keys:
            continue
        str_val = str(v).strip() if v is not None else ""
        existing = session.exec(
            select(Setting).where(Setting.key == k, Setting.category == "application_defaults")
        ).first()
        if existing:
            existing.value = str_val
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
        else:
            session.add(Setting(key=k, value=str_val, category="application_defaults"))
        updated.append(k)

    session.add(AuditLog(
        action="application_defaults_updated",
        entity_type="setting",
        details=f"Updated application defaults: {', '.join(updated)}",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    return {"success": True, "updated": updated, "defaults": load_application_defaults(session)}


@router.post("/browser-login")
async def launch_portal_login_browser(body: dict):
    """Launch visible persistent Playwright browser to manually sign in to Naukri / LinkedIn / Workday.

    Session cookies are persisted in BROWSER_PROFILE_DIR so automated appliers stay logged in.
    """
    portal = (body.get("portal") or "naukri").lower().strip()
    custom_url = (body.get("url") or "").strip()
    portal_urls = {
        "naukri": "https://www.naukri.com/nlogin/login",
        "linkedin": "https://www.linkedin.com/login",
        "workday": custom_url or "https://www.myworkday.com/",
    }
    target_url = custom_url or portal_urls.get(portal)
    if not target_url:
        raise HTTPException(status_code=400, detail="Unsupported portal")

    env_settings = get_settings()
    profile_dir = env_settings.BROWSER_PROFILE_DIR
    os.makedirs(profile_dir, exist_ok=True)

    import subprocess, sys
    helper_code = (
        "import time\n"
        "from playwright.sync_api import sync_playwright\n"
        f"with sync_playwright() as p:\n"
        f"    ctx = p.chromium.launch_persistent_context({profile_dir!r}, headless=False, args=['--start-maximized'])\n"
        f"    page = ctx.pages[0] if ctx.pages else ctx.new_page()\n"
        f"    page.goto({target_url!r}, timeout=45000)\n"
        "    try:\n"
        "        while ctx.pages:\n"
        "            time.sleep(1)\n"
        "    except Exception:\n"
        "        pass\n"
    )
    subprocess.Popen([sys.executable, "-c", helper_code])
    return {
        "success": True,
        "portal": portal,
        "url": target_url,
        "profile_dir": profile_dir,
        "message": f"Opened browser window to {target_url}. Sign in manually, then close the browser window when done.",
    }


@router.put("/{key}")
async def update_setting(key: str, body: dict[str, Any], session: Session = Depends(get_session)):
    """Update a setting in the database. Body: {value: str, category?: str}."""
    value = body.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="'value' is required")
    category = body.get("category", "general")

    existing = session.exec(select(Setting).where(Setting.key == key)).first()
    if existing:
        existing.value = str(value)
        existing.category = category
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
    else:
        setting = Setting(
            key=key,
            value=str(value),
            category=category,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(setting)

    # Audit log
    session.add(AuditLog(
        action="setting_updated",
        entity_type="setting",
        details=f"Key '{key}' updated",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    return {"key": key, "value": str(value), "category": category}


@router.delete("/{key}")
async def delete_setting(key: str, session: Session = Depends(get_session)):
    """Delete a setting."""
    existing = session.exec(select(Setting).where(Setting.key == key)).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Setting not found")
    session.delete(existing)
    session.commit()
    return {"deleted": key}


# ─── .env file updates ──────────────────────────────────────


@router.put("/env/{key}")
async def update_env_setting(key: str, body: dict[str, Any], session: Session = Depends(get_session)):
    """Update a value in the .env file. Allowed keys are whitelisted."""
    allowed_keys = {
        "DEFAULT_PROVIDER", "MISTRAL_API_KEY", "NVIDIA_API_KEY",
        "MISTRAL_STRONG_MODEL", "MISTRAL_CHEAP_MODEL",
        "NVIDIA_STRONG_MODEL", "NVIDIA_CHEAP_MODEL",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "FERNET_KEY", "LOG_LEVEL",
    }
    if key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"Key '{key}' is not allowed to be updated via API")

    value = body.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="'value' is required")

    # Find .env file
    env_path = _find_env_file()
    if not env_path:
        raise HTTPException(status_code=500, detail=".env file not found")

    # Read, update, write
    _update_env_file(env_path, key, str(value))

    # Update runtime environment variable so pydantic-settings and os.getenv pick it up
    os.environ[key] = str(value)

    # Clear settings cache so next read picks up new values
    get_settings.cache_clear()

    # Reset LLM router if provider settings changed
    if key in {"DEFAULT_PROVIDER", "MISTRAL_API_KEY", "NVIDIA_API_KEY",
               "MISTRAL_STRONG_MODEL", "MISTRAL_CHEAP_MODEL",
               "NVIDIA_STRONG_MODEL", "NVIDIA_CHEAP_MODEL"}:
        try:
            from llm.router import reset_router
            reset_router()
        except ImportError:
            pass

    # Audit log
    display_value = _mask(str(value)) if "KEY" in key or "TOKEN" in key else str(value)
    session.add(AuditLog(
        action="env_setting_updated",
        entity_type="env",
        details=f"Env key '{key}' updated to '{display_value}'",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    return {"key": key, "value": display_value}


# ─── Portal Accounts ────────────────────────────────────────


@router.get("/portals")
async def get_portal_accounts(session: Session = Depends(get_session)):
    """Get all portal accounts (passwords masked)."""
    accounts = session.exec(select(PortalAccount)).all()
    result = []
    for a in accounts:
        result.append({
            "id": a.id,
            "portal": a.portal,
            "tenant": a.tenant,
            "username": a.username,
            "has_password": bool(a.encrypted_password),
            "is_active": a.is_active,
            "last_login": a.last_login.isoformat() if a.last_login else None,
        })
    return result


@router.post("/portals")
async def create_portal_account(body: dict[str, Any], session: Session = Depends(get_session)):
    """Create a portal account with encrypted password."""
    portal = body.get("portal", "")
    username = body.get("username", "")
    password = body.get("password", "")
    tenant = body.get("tenant", "")

    if not portal or not username:
        raise HTTPException(status_code=400, detail="portal and username are required")

    encrypted_pw = encrypt_value(password) if password else ""

    account = PortalAccount(
        portal=portal,
        tenant=tenant,
        username=username,
        encrypted_password=encrypted_pw,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(account)
    session.add(AuditLog(
        action="portal_account_created",
        entity_type="portal_account",
        details=f"Account for {portal}" + (f" ({tenant})" if tenant else ""),
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    session.refresh(account)

    return {"id": account.id, "portal": portal, "username": username, "tenant": tenant}


@router.delete("/portals/{account_id}")
async def delete_portal_account(account_id: int, session: Session = Depends(get_session)):
    """Delete a portal account."""
    account = session.get(PortalAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    session.delete(account)
    session.commit()
    return {"deleted": account_id}


# ─── LLM Usage Stats ────────────────────────────────────────


@router.get("/llm-stats")
async def get_llm_stats(session: Session = Depends(get_session)):
    """Get LLM usage statistics."""
    from sqlmodel import func
    from models.audit import LLMCall

    stats = session.exec(
        select(
            LLMCall.provider,
            LLMCall.model,
            func.count(LLMCall.id).label("calls"),
            func.sum(LLMCall.total_tokens).label("total_tokens"),
            func.sum(LLMCall.cost).label("total_cost"),
        ).group_by(LLMCall.provider, LLMCall.model)
    ).all()

    return [
        {
            "provider": row[0],
            "model": row[1],
            "calls": row[2],
            "total_tokens": row[3] or 0,
            "total_cost": round(row[4] or 0, 6),
        }
        for row in stats
    ]


# ─── Audit Log ───────────────────────────────────────────────


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """Get recent audit log entries."""
    logs = session.exec(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())  # type: ignore
        .offset(offset)
        .limit(limit)
    ).all()
    return logs


# ─── LLM Configuration & Test ────────────────────────────────


@router.get("/llm")
async def get_llm_config():
    """Get current LLM configuration and status for Mistral and NVIDIA (Nemotron)."""
    settings = get_settings()
    return {
        "default_provider": settings.DEFAULT_PROVIDER,
        "mistral": {
            "configured": bool(settings.MISTRAL_API_KEY and settings.MISTRAL_API_KEY != "your-mistral-api-key"),
            "api_key_masked": _mask(settings.MISTRAL_API_KEY),
            "strong_model": settings.MISTRAL_STRONG_MODEL,
            "cheap_model": settings.MISTRAL_CHEAP_MODEL,
        },
        "nvidia": {
            "configured": bool(settings.NVIDIA_API_KEY and settings.NVIDIA_API_KEY != "your-nvidia-api-key"),
            "api_key_masked": _mask(settings.NVIDIA_API_KEY),
            "strong_model": settings.NVIDIA_STRONG_MODEL,
            "cheap_model": settings.NVIDIA_CHEAP_MODEL,
        },
    }


@router.post("/llm")
async def configure_llm(body: dict[str, Any], session: Session = Depends(get_session)):
    """Configure Mistral and NVIDIA (Nemotron) API settings.
    
    Accepts:
    - default_provider: 'mistral' | 'nvidia'
    - mistral_api_key: str
    - mistral_strong_model: str
    - mistral_cheap_model: str
    - nvidia_api_key: str
    - nvidia_strong_model: str
    - nvidia_cheap_model: str
    """
    env_path = _find_env_file()
    if not env_path:
        raise HTTPException(status_code=500, detail=".env file not found")

    mapping = {
        "default_provider": "DEFAULT_PROVIDER",
        "mistral_api_key": "MISTRAL_API_KEY",
        "mistral_strong_model": "MISTRAL_STRONG_MODEL",
        "mistral_cheap_model": "MISTRAL_CHEAP_MODEL",
        "nvidia_api_key": "NVIDIA_API_KEY",
        "nvidia_strong_model": "NVIDIA_STRONG_MODEL",
        "nvidia_cheap_model": "NVIDIA_CHEAP_MODEL",
    }

    updated_keys = []
    for payload_key, env_var in mapping.items():
        if payload_key in body and body[payload_key] is not None:
            val = str(body[payload_key]).strip()
            _update_env_file(env_path, env_var, val)
            os.environ[env_var] = val
            updated_keys.append(env_var)

    get_settings.cache_clear()

    try:
        from llm.router import reset_router
        reset_router()
    except ImportError:
        pass

    session.add(AuditLog(
        action="llm_config_updated",
        entity_type="llm_settings",
        details=f"Updated keys: {', '.join(updated_keys)}",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    return await get_llm_config()


@router.post("/test-llm")
async def test_llm_connection(body: dict[str, Any] = {}):
    """Test LLM provider connectivity.
    
    Accepts:
    - provider: 'mistral' | 'nvidia' (defaults to DEFAULT_PROVIDER)
    - api_key: optional key to test before saving
    - model: optional model name override
    """
    import time
    settings = get_settings()
    provider_name = body.get("provider") or settings.DEFAULT_PROVIDER or "mistral"
    api_key_override = body.get("api_key")
    model_override = body.get("model")

    start_time = time.perf_counter()

    try:
        from llm.provider import LLMMessage

        # If an explicit API key or model override was passed, instantiate provider directly
        if api_key_override or model_override or provider_name:
            if provider_name == "mistral":
                from llm.mistral import MistralProvider
                provider_instance = MistralProvider(
                    api_key=api_key_override,
                    strong_model=model_override,
                    cheap_model=model_override,
                )
                test_model = model_override or provider_instance.get_model("cheap")
                response = await provider_instance.chat(
                    messages=[LLMMessage(role="user", content="Respond with exactly: OK")],
                    model=test_model,
                    temperature=0.0,
                )
            elif provider_name in ("nvidia", "nemotron"):
                from llm.nvidia import NvidiaProvider
                provider_instance = NvidiaProvider(
                    api_key=api_key_override,
                    strong_model=model_override,
                    cheap_model=model_override,
                )
                test_model = model_override or provider_instance.get_model("cheap")
                response = await provider_instance.chat(
                    messages=[LLMMessage(role="user", content="Respond with exactly: OK")],
                    model=test_model,
                    temperature=0.0,
                )
            else:
                from llm.router import get_router
                router = get_router()
                response = await router.chat(
                    messages=[LLMMessage(role="user", content="Respond with exactly: OK")],
                    task="cheap",
                    provider=provider_name,
                    temperature=0.0,
                )
        else:
            from llm.router import get_router
            router = get_router()
            response = await router.chat(
                messages=[LLMMessage(role="user", content="Respond with exactly: OK")],
                task="cheap",
                temperature=0.0,
            )

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "success": True,
            "provider": response.provider,
            "model": response.model,
            "response": response.content.strip()[:100],
            "tokens": response.total_tokens,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "success": False,
            "provider": provider_name,
            "error": str(e),
            "latency_ms": latency_ms,
        }


# ─── Helpers ─────────────────────────────────────────────────


def _mask(value: str) -> str:
    """Mask sensitive values for display."""
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]


def _find_env_file() -> str | None:
    """Find the .env file."""
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.getcwd()), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _update_env_file(path: str, key: str, value: str):
    """Update or append a key=value pair in the .env file."""
    lines = []
    found = False
    with open(path, "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(path, "w") as f:
        f.writelines(new_lines)

