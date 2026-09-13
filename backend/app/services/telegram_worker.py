"""At-least-once inbox processing and ticket delivery, coordinated by PostgreSQL."""
import asyncio
import logging
from datetime import timedelta

from sqlalchemy import delete, select, text

from app.models.telegram import TelegramDelivery, TelegramUpdate
from app.services.reservation import ReservationService
from app.services.telegram_bot import TelegramAPIError
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
LOCK_ID = 637492017


async def process_one(bot, sessions):
    async with sessions() as session:
        update = await session.scalar(select(TelegramUpdate).where(
            TelegramUpdate.processed_at.is_(None), TelegramUpdate.available_at <= utcnow(),
            TelegramUpdate.attempts < 8).order_by(TelegramUpdate.update_id).limit(1))
        if not update:
            return False
        update_id, payload = update.update_id, update.payload
        try:
            await bot.handle_update(payload, session)
        except Exception as error:
            await session.rollback()
            update = await session.get(TelegramUpdate, update_id, populate_existing=True)
            update.attempts += 1
            update.last_error = type(error).__name__
            delay = max(min(2 ** update.attempts, 300), getattr(error, "retry_after", 0))
            update.available_at = utcnow() + timedelta(seconds=delay)
            logger.warning("telegram_update_retry update_id=%s attempt=%s error=%s", update_id, update.attempts, type(error).__name__)
        else:
            update = await session.get(TelegramUpdate, update_id)
            update.processed_at = utcnow()
            update.payload = {}  # Do not retain phone/message payloads after processing.
            update.last_error = None
            logger.info("telegram_update_processed update_id=%s", update_id)
        await session.commit()
        return True


async def deliver_one(bot, sessions):
    async with sessions() as session:
        delivery = await session.scalar(select(TelegramDelivery).where(
            TelegramDelivery.sent_at.is_(None), TelegramDelivery.attempts < 8,
            TelegramDelivery.available_at <= utcnow()).order_by(TelegramDelivery.available_at).limit(1))
        if not delivery:
            return False
        ticket_id = delivery.ticket_id
        try:
            await bot.send_ticket(session, delivery)
        except Exception as error:
            await session.rollback()
            delivery = await session.get(TelegramDelivery, ticket_id, populate_existing=True)
            delivery.attempts += 1
            delivery.last_error = type(error).__name__
            delivery.available_at = utcnow() + timedelta(seconds=max(min(2 ** delivery.attempts, 300), getattr(error, "retry_after", 0)))
            if isinstance(error, TelegramAPIError) and error.code == 403:
                delivery.attempts = 8  # Recipient blocked the bot; /tickets can request a resend.
            logger.warning("telegram_ticket_retry ticket_id=%s error=%s", ticket_id, type(error).__name__)
        else:
            delivery.sent_at = utcnow()
            delivery.last_error = None
        await session.commit()
        return True


async def run_worker(bot, sessions, engine):
    configured = False
    while True:
        try:
            if not configured:
                await bot.setup()
                configured = True
            # Dedicated session-level lock survives the business services' commits.
            async with engine.connect() as lock_connection:
                acquired = await lock_connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_ID})
                await lock_connection.commit()
                if not acquired:
                    await asyncio.sleep(3)
                    continue
                try:
                    last_maintenance = utcnow() - timedelta(minutes=1)
                    logger.info("telegram_worker_started")
                    while True:
                        await lock_connection.execute(text("SELECT 1"))
                        await lock_connection.commit()
                        worked = await process_one(bot, sessions)
                        delivered = await deliver_one(bot, sessions)
                        if utcnow() - last_maintenance >= timedelta(seconds=30):
                            async with sessions() as session:
                                await ReservationService(session).expire_pending_reservations()
                                await session.execute(delete(TelegramUpdate).where(TelegramUpdate.processed_at < utcnow() - timedelta(days=7)))
                                await session.commit()
                            last_maintenance = utcnow()
                        await asyncio.sleep(0.05 if worked or delivered else 1)
                finally:
                    try:
                        if not lock_connection.invalidated:
                            await lock_connection.rollback()
                            await lock_connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
                            await lock_connection.commit()
                    except Exception:
                        await lock_connection.invalidate()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # Exception strings from HTTP clients may contain the bot token.
            logger.error("telegram_worker_error type=%s", type(error).__name__)
            await asyncio.sleep(5)
