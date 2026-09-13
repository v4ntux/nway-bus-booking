import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import db_session
from app.core.config import get_settings
from app.models.telegram import TelegramUpdate

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook", include_in_schema=False)
async def telegram_webhook(request: Request, session=Depends(db_session)):
    settings = get_settings()
    if not settings.TELEGRAM_BOT_ENABLED or not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(503, "Telegram is not configured")
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(supplied.encode(), settings.TELEGRAM_WEBHOOK_SECRET.encode()):
        raise HTTPException(403, "Invalid webhook secret")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            raise HTTPException(413, "Update too large")
    try:
        update = json.loads(body)
        update_id = update["update_id"]
        if type(update_id) is not int or update_id < 0:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Invalid update") from None
    await session.execute(insert(TelegramUpdate).values(update_id=update_id, payload=update, attempts=0).on_conflict_do_nothing(index_elements=[TelegramUpdate.update_id]))
    await session.commit()
    return {"ok": True}
