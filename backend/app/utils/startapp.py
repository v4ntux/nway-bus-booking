"""Compact Mini App start parameters.

Telegram limits `startapp` to 64 characters of [A-Za-z0-9_-]. A UUID in base64url
is 22 characters, so a route (two cities) fits as "r" + 44 characters.
"""
import base64
from uuid import UUID


def encode_uuid(value: UUID) -> str:
    return base64.urlsafe_b64encode(value.bytes).decode().rstrip("=")


def decode_uuid(value: str) -> UUID:
    return UUID(bytes=base64.urlsafe_b64decode(value + "=="))


def route_param(origin_id: UUID, destination_id: UUID) -> str:
    return "r" + encode_uuid(origin_id) + encode_uuid(destination_id)
