"""Health check endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from app.database import get_session
from app.config import get_settings
from services.scheduler import get_scheduler_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: Session = Depends(get_session)):
    """System health check with component status."""
    settings = get_settings()

    # Check database
    db_ok = False
    try:
        session.exec(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Check LLM providers
    providers = {}
    mistral_configured = bool(settings.MISTRAL_API_KEY and not settings.MISTRAL_API_KEY.startswith("your-"))
    if mistral_configured:
        providers["mistral"] = {"configured": True, "model_strong": settings.MISTRAL_STRONG_MODEL, "model_cheap": settings.MISTRAL_CHEAP_MODEL}
    else:
        providers["mistral"] = {"configured": False}

    nvidia_configured = bool(settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("your-"))
    if nvidia_configured:
        providers["nvidia"] = {"configured": True, "model_strong": settings.NVIDIA_STRONG_MODEL, "model_cheap": settings.NVIDIA_CHEAP_MODEL}
    else:
        providers["nvidia"] = {"configured": False}

    # Check encryption
    encryption_ok = bool(settings.FERNET_KEY and not settings.FERNET_KEY.startswith("your-") and len(settings.FERNET_KEY) > 10)

    # Check Telegram
    telegram_ok = bool(
        settings.TELEGRAM_BOT_TOKEN
        and not settings.TELEGRAM_BOT_TOKEN.startswith("your-")
        and settings.TELEGRAM_CHAT_ID
        and not settings.TELEGRAM_CHAT_ID.startswith("your-")
    )

    all_ok = db_ok and any(p["configured"] for p in providers.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": {"status": "up" if db_ok else "down"},
            "llm_providers": providers,
            "default_provider": settings.DEFAULT_PROVIDER,
            "encryption": {"status": "configured" if encryption_ok else "not_configured"},
            "telegram": {"status": "configured" if telegram_ok else "not_configured"},
            "scheduler": get_scheduler_status(),
        },
    }

