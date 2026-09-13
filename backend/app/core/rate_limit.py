"""Redis-ready rate limit hooks. MVP is a no-op; do not treat this as security."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RateLimiter(ABC):
    @abstractmethod
    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        """Raise DomainError(code=RATE_LIMITED) when exceeded."""


class NoOpRateLimiter(RateLimiter):
    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        logger.debug("rate_limit_skip key=%s limit=%s window=%s", key, limit, window_seconds)


rate_limiter: RateLimiter = NoOpRateLimiter()
