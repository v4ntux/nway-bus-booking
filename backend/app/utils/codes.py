import secrets
import string


_LETTERS = string.ascii_uppercase
_ALNUM = string.ascii_uppercase + string.digits


def generate_booking_code() -> str:
    prefix = "".join(secrets.choice(_LETTERS) for _ in range(3))
    suffix = "".join(secrets.choice(_ALNUM) for _ in range(5))
    return f"{prefix}-{suffix}"


def generate_ticket_public_id() -> str:
    return "T" + "".join(secrets.choice(_ALNUM) for _ in range(8))


def generate_qr_token() -> str:
    return secrets.token_urlsafe(32)
