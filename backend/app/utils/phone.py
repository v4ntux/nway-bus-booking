import phonenumbers
from phonenumbers import NumberParseException

from app.core.exceptions import DomainError


def normalize_phone(raw: str, default_region: str | None = None) -> str:
    value = (raw or "").strip()
    if not value:
        raise DomainError("INVALID_PHONE", "Phone number is required")
    try:
        parsed = phonenumbers.parse(value, default_region)
    except NumberParseException as exc:
        raise DomainError("INVALID_PHONE", "Invalid phone number") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise DomainError("INVALID_PHONE", "Invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
