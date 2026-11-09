"""Telegram Bot Notification Service."""

import logging
from typing import Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_telegram_message(text: str) -> bool:
    """Send alert or notification to configured Telegram chat."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id or token.startswith("your-"):
        logger.debug("Telegram notifications not configured; skipping.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.warning("Telegram API error %d: %s", resp.status_code, resp.text)
                return False
    except Exception as exc:
        logger.error("Failed sending Telegram message: %s", exc)
        return False


async def notify_new_matches(count: int, top_job_title: str, top_company: str):
    """Notify user of newly discovered high-matching jobs."""
    msg = (
        f"🎯 *New Job Matches Found!*\n\n"
        f"Discovered *{count}* high-scoring opportunities.\n"
        f"Top match: *{top_job_title}* at *{top_company}*.\n\n"
        f"Review them in your dashboard: http://localhost:3000"
    )
    await send_telegram_message(msg)


async def notify_captcha_alert(portal: str, job_url: str):
    """Alert user that automation paused due to a CAPTCHA challenge."""
    msg = (
        f"⚠️ *CAPTCHA Challenge Encountered!*\n\n"
        f"Portal: *{portal.capitalize()}*\n"
        f"Automation paused safely. Solve it in your browser session.\n"
        f"URL: {job_url}"
    )
    await send_telegram_message(msg)


async def notify_application_submitted(job_title: str, company: str, portal: str):
    """Notify user of a completed application submission."""
    msg = (
        f"✅ *Application Submitted!*\n\n"
        f"Position: *{job_title}*\n"
        f"Company: *{company}*\n"
        f"Portal: *{portal.capitalize()}*"
    )
    await send_telegram_message(msg)

