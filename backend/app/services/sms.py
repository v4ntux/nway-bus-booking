import logging
import secrets
import string

logger = logging.getLogger(__name__)


class SmsProvider:
    def generate_code(self, length: int = 6) -> str:
        return "".join(secrets.choice(string.digits) for _ in range(length))

    async def send(self, phone: str, code: str) -> None:
        raise NotImplementedError


class MockSmsProvider(SmsProvider):
    def __init__(self) -> None:
        self.last_codes: dict[str, str] = {}

    async def send(self, phone: str, code: str) -> None:
        self.last_codes[phone] = code
        logger.info("mock_sms phone=%s code=%s", phone, code)


sms_provider: SmsProvider = MockSmsProvider()
