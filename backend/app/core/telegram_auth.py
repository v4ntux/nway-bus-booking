"""Verify Mini App identity on the server; never trust initDataUnsafe."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError


def validate_init_data(raw: str, token: str, *, now: float | None = None) -> int:
    try:
        if not token or not raw or len(raw) > 8192:
            raise ValueError()
        pairs = parse_qsl(raw, strict_parsing=True)
        data = dict(pairs)
        if len(data) != len(pairs):
            raise ValueError()
        supplied_hash = data.pop("hash")
        check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied_hash):
            raise ValueError()
        age = (time.time() if now is None else now) - int(data["auth_date"])
        if not -30 <= age <= 3600:
            raise ValueError()
        user = json.loads(data["user"])
        chat_id = user["id"]
        if type(chat_id) is not int or not 0 < chat_id < 2**63 or user.get("is_bot"):
            raise ValueError()
        return chat_id
    except (ValueError, KeyError, TypeError, OverflowError):
        raise UnauthorizedError("TELEGRAM_AUTH_INVALID", "Telegram ilovasini yopib, botdan qayta oching.") from None


def optional_telegram_user(x_telegram_init_data: str | None = Header(default=None)) -> int | None:
    if x_telegram_init_data is None:
        return None
    return validate_init_data(x_telegram_init_data, get_settings().TELEGRAM_BOT_TOKEN)
