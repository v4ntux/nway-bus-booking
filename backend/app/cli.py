import argparse
import asyncio
import logging

from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.services.reservation import ReservationService
from app.services.seed import seed_database
from app.services.telegram_bot import run_telegram_bot
from app.services.telegram_bot import TelegramBotClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def cmd_seed() -> None:
    async with SessionLocal() as session:
        await seed_database(session)


async def cmd_expire() -> None:
    async with SessionLocal() as session:
        count = await ReservationService(session).expire_pending_reservations()
        logger.info("expired_reservations count=%s", count)


async def cmd_telegram_webhook(url: str) -> None:
    from urllib.parse import urlparse
    settings = get_settings()
    if urlparse(url).scheme != "https" or not urlparse(url).hostname:
        raise SystemExit("Use the backend's public HTTPS URL")
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_WEBHOOK_SECRET:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET first")
    bot = TelegramBotClient(settings.TELEGRAM_BOT_TOKEN)
    try:
        await bot.setup()
        await bot._call("setWebhook", url=url.rstrip("/") + "/telegram/webhook",
                        secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                        allowed_updates=["message", "callback_query"], max_connections=10)
        print(f"Telegram webhook configured for @{bot.username}")
    finally:
        await bot.close()


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(prog="nway")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="Insert demo data")
    sub.add_parser("expire-reservations", help="Expire holds and unpaid bookings past deadline")
    sub.add_parser("telegram-bot", help="Run the durable Telegram inbox worker")
    webhook = sub.add_parser("telegram-webhook", help="Register the Telegram webhook")
    webhook.add_argument("--url", required=True, help="Backend public HTTPS origin")
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(cmd_seed())
    elif args.command == "expire-reservations":
        asyncio.run(cmd_expire())
    elif args.command == "telegram-bot":
        asyncio.run(run_telegram_bot())
    elif args.command == "telegram-webhook":
        asyncio.run(cmd_telegram_webhook(args.url))


if __name__ == "__main__":
    main()
