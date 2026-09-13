import argparse
import asyncio
import logging

from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.services.reservation import ReservationService
from app.services.seed import seed_database
from app.services.telegram_bot import run_telegram_bot

logger = logging.getLogger(__name__)


async def cmd_seed() -> None:
    async with SessionLocal() as session:
        await seed_database(session)


async def cmd_expire() -> None:
    async with SessionLocal() as session:
        count = await ReservationService(session).expire_pending_reservations()
        logger.info("expired_reservations count=%s", count)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(prog="nway")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="Insert demo data")
    sub.add_parser("expire-reservations", help="Expire holds and unpaid bookings past deadline")
    sub.add_parser("telegram-bot", help="Run Telegram bot (polling) with Mini App menu")
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(cmd_seed())
    elif args.command == "expire-reservations":
        asyncio.run(cmd_expire())
    elif args.command == "telegram-bot":
        asyncio.run(run_telegram_bot())


if __name__ == "__main__":
    main()
