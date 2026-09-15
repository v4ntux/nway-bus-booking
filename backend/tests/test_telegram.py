import asyncio
from datetime import timedelta
from io import BytesIO
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models import Payment, PaymentStatus, Reservation, ReservationStatus, Ticket, TicketStatus
from app.models.telegram import TelegramChat, TelegramDelivery, TelegramUpdate
from app.services.payment import PaymentService
from app.services.telegram_bot import TelegramAPIError, TelegramBotClient, button, money
from app.services.telegram_worker import deliver_one, poll_updates, process_one
from app.services.ticket import TicketService
from app.services.trip import TripService
from app.utils.time import utcnow


class FakeTelegram(TelegramBotClient):
    def __init__(self):
        self.calls = []
        self.fail_photo = False

    async def _call(self, method, **payload):
        if method == "sendPhoto" and self.fail_photo:
            raise TelegramAPIError(method, 429, 1)
        self.calls.append((method, payload))
        return {"message_id": len(self.calls)}


def update(*, action=None, text=None, contact=None, chat_id=4242, update_id=1):
    sender = {"id": chat_id, "first_name": "Али", "last_name": "Каримов"}
    message = {"message_id": 10, "chat": {"id": chat_id, "type": "private"}, "from": sender}
    if action:
        return {"update_id": update_id, "callback_query": {"id": str(update_id), "from": sender, "message": message, "data": action}}
    if text:
        message["text"] = text
    if contact:
        message["contact"] = contact
    return {"update_id": update_id, "message": message}


async def prepare_checkout(bot, engine, world, chat_id=4242, phone="998901234567"):
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def send(**kwargs):
        async with sessions() as session:
            await bot.handle_update(update(chat_id=chat_id, **kwargs), session)

    await send(text="/start")
    await send(action="book")
    await send(action=f"o:{world['origin'].id}")
    await send(action=f"d:{world['dest'].id}")
    day = world["trip"].departure_datetime.astimezone(ZoneInfo(world["origin"].timezone)).date()
    await send(action=f"dt:{day.isoformat()}")
    await send(action=f"tr:{world['trip'].id}")
    await send(action=f"s:{world['seats'][0].id}")
    await send(action="passenger")
    await send(contact={"user_id": chat_id, "phone_number": phone})
    await send(action="nameok")
    async with sessions() as session:
        chat = await session.get(TelegramChat, chat_id)
        assert chat.data["stage"] == "review"
        nonce = chat.data["nonce"]
    return send, nonce, sessions


async def test_full_bot_booking_survives_new_sessions_and_sends_png(engine, world):
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    await send(action=f"ok:{nonce}")  # repeated tap / retried update
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Reservation)) == 1
        booking = await session.scalar(select(Reservation))
        assert booking.status == ReservationStatus.confirmed
        assert booking.payment_status == PaymentStatus.unpaid
        assert await session.scalar(select(func.count()).select_from(Ticket)) == 1
        assert await session.scalar(select(func.count()).select_from(TelegramDelivery)) == 1
        code = booking.public_code
    assert await deliver_one(bot, sessions)
    photos = [payload for method, payload in bot.calls if method == "sendPhoto"]
    assert len(photos) == 1
    assert photos[0]["chat_id"] == 4242
    image = Image.open(BytesIO(photos[0]["_photo"]))
    assert image.size == (1080, 1550)
    assert image.format == "PNG"
    assert "To‘lov chiqishda" in photos[0]["caption"]
    assert not await deliver_one(bot, sessions)
    await send(action=f"image:{code}")
    assert await deliver_one(bot, sessions)
    assert len([p for m, p in bot.calls if m == "sendPhoto"]) == 2
    for _, payload in bot.calls:
        for row in payload.get("reply_markup", {}).get("inline_keyboard", []):
            assert len(row) <= 8
            assert all(len(b["callback_data"].encode()) <= 64 for b in row)


async def test_bot_cancellation_invalidates_qr_and_releases_seat(engine, world):
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        booking = await session.scalar(select(Reservation))
        ticket = await session.scalar(select(Ticket))
        code, token = booking.public_code, ticket.qr_token
    await send(action=f"cancelask:{code}")
    async with sessions() as session:
        assert (await session.scalar(select(Reservation))).status == ReservationStatus.confirmed
    await send(action=f"cancel:{code}")
    async with sessions() as session:
        assert (await session.scalar(select(Ticket))).status == TicketStatus.cancelled
        with pytest.raises(DomainError, match="cancelled"):
            await TicketService(session).verify_qr(token)
    assert await deliver_one(bot, sessions)
    assert not [p for m, p in bot.calls if m == "sendPhoto"]


async def test_other_telegram_user_cannot_access_or_cancel_booking(engine, world):
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        booking = await session.scalar(select(Reservation))
        code = booking.public_code
    for action in (f"view:{code}", f"image:{code}", f"cancel:{code}"):
        async with sessions() as session:
            await bot.handle_update(update(action=action, chat_id=9999), session)
        # The refusal must not leak the booking code or trip details to a stranger.
        assert code not in bot.calls[-1][1]["text"]
        assert not [p for m, p in bot.calls if m == "sendPhoto"]
    async with sessions() as session:
        assert (await session.scalar(select(Reservation))).status == ReservationStatus.confirmed


async def test_foreign_contact_does_not_link_account(engine, world):
    bot = FakeTelegram()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(TelegramChat(chat_id=4242, data={"stage": "phone"}))
        await session.commit()
        await bot.handle_update(update(contact={"user_id": 9999, "phone_number": "998901234567"}), session)
    async with sessions() as session:
        assert (await session.get(TelegramChat, 4242)).phone is None
    assert "своим номером" in bot.calls[-1][1]["text"]


async def test_delivery_failure_persists_and_retries_without_duplicate_booking(engine, world):
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    bot.fail_photo = True
    assert await deliver_one(bot, sessions)
    async with sessions() as session:
        delivery = await session.scalar(select(TelegramDelivery))
        assert delivery.sent_at is None and delivery.attempts == 1
        delivery.available_at = utcnow() - timedelta(seconds=1)
        await session.commit()
    bot.fail_photo = False
    assert await deliver_one(bot, sessions)
    assert len([p for m, p in bot.calls if m == "sendPhoto"]) == 1


async def test_webhook_requires_secret_and_deduplicates(client, session, monkeypatch):
    monkeypatch.setattr(get_settings(), "TELEGRAM_BOT_ENABLED", True)
    monkeypatch.setattr(get_settings(), "TELEGRAM_WEBHOOK_SECRET", "test-secret")
    payload = update(text="/start", update_id=918)
    assert (await client.post("/telegram/webhook", json=payload)).status_code == 403
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    for _ in range(2):
        assert (await client.post("/telegram/webhook", json=payload, headers=headers)).status_code == 200
    assert await session.scalar(select(func.count()).select_from(TelegramUpdate)) == 1
    assert (await client.post("/telegram/webhook", content=b"x" * 65537, headers=headers)).status_code == 413


async def test_inbox_processes_once_and_redacts_payload(engine, world):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(TelegramUpdate(update_id=123, payload=update(text="/start")))
        await session.commit()
    bot = FakeTelegram()
    assert await process_one(bot, sessions)
    count = len(bot.calls)
    assert not await process_one(bot, sessions)
    assert len(bot.calls) == count
    async with sessions() as session:
        record = await session.get(TelegramUpdate, 123)
        assert record.processed_at and record.payload == {}


async def test_bot_bookings_not_exposed_by_public_codes(client, engine, world):
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        booking = await session.scalar(select(Reservation))
        ticket = await session.scalar(select(Ticket))
        code, ticket_id = booking.public_code, ticket.public_id
    for path in (f"/reservations/{code}", f"/reservations/{code}/tickets", f"/tickets/{ticket_id}"):
        assert (await client.get("/api/v1" + path)).status_code == 404
    assert (await client.post(f"/api/v1/reservations/{code}/cancel")).status_code == 404
    assert (await client.post("/api/v1/tickets/verify", json={"qr_token": "anything"})).status_code == 401


async def test_cash_payment_can_be_recorded_after_bot_confirmation(engine, world):
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        booking = await session.scalar(select(Reservation))
        service = PaymentService(session)
        payment = await service.mark_paid_offline(booking.id, world["admin"].id)
        repeated = await service.mark_paid_offline(booking.id, world["admin"].id)
        assert payment.id == repeated.id
        assert await session.scalar(select(func.count()).select_from(Payment)) == 1
        assert booking.payment_status == PaymentStatus.paid


async def test_mock_payments_are_disabled_by_default(world, monkeypatch):
    monkeypatch.setattr(get_settings(), "ALLOW_MOCK_PAYMENTS", False)
    with pytest.raises(DomainError, match="disabled"):
        await PaymentService(world["session"]).mock_success(world["trip"].id)


def test_callback_budget_and_price_format():
    assert money(9_500_000) == "95 000 so‘m"
    assert money(12345) == "123,45 so‘m"
    with pytest.raises(ValueError):
        button("too long", "ю" * 33)


async def test_staff_can_record_cash_and_board_only_once(engine, world):
    from app.services import telegram_admin
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        chat = TelegramChat(chat_id=8888, user_id=world["admin"].id, phone=world["admin"].phone, data={})
        session.add(chat)
        await session.commit()
        booking = await session.scalar(select(Reservation))
        ticket = await session.scalar(select(Ticket))
        await telegram_admin.booking(bot, session, chat, booking.public_code, action="paid")
        await telegram_admin.check(bot, session, chat, ticket.public_id)
        assert ticket.status == TicketStatus.valid
        await telegram_admin.check(bot, session, chat, ticket.public_id, board=True)
        assert ticket.status == TicketStatus.used
        with pytest.raises(DomainError, match="already used"):
            await telegram_admin.check(bot, session, chat, ticket.public_id, board=True)


async def test_passenger_cannot_open_staff_actions(engine, world):
    from app.services import telegram_admin
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        chat = await session.get(TelegramChat, 4242)
        booking = await session.scalar(select(Reservation))
        with pytest.raises(DomainError, match="сотрудникам"):
            await telegram_admin.booking(bot, session, chat, booking.public_code, action="paid")


async def test_departure_search_uses_origin_timezone(world):
    from datetime import datetime, time
    session = world["session"]
    origin, trip = world["origin"], world["trip"]
    origin.timezone = "Asia/Tashkent"
    day = utcnow().astimezone(ZoneInfo(origin.timezone)).date() + timedelta(days=3)
    trip.departure_datetime = datetime.combine(day, time(1, 0), tzinfo=ZoneInfo(origin.timezone))
    await session.commit()
    assert (await TripService(session).search(origin.id, world["dest"].id, day))[0]["trip"].id == trip.id
    assert not await TripService(session).search(origin.id, world["dest"].id, day - timedelta(days=1))


async def test_other_staff_company_cannot_open_ticket(engine, world):
    from uuid import uuid4
    from app.services import telegram_admin
    from app.models import User, UserRole, UserStatus
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        outsider = User(phone="+998905555555", role=UserRole.operator, status=UserStatus.active)
        session.add(outsider)
        await session.flush()
        chat = TelegramChat(chat_id=7777, user_id=outsider.id, phone=outsider.phone, data={})
        session.add(chat)
        await session.commit()
        ticket = await session.scalar(select(Ticket))
        with pytest.raises(DomainError, match="другому перевозчику"):
            await telegram_admin.check(bot, session, chat, ticket.public_id)


class PollingBot(FakeTelegram):
    """Serves canned getUpdates batches, then cancels to end the endless poll loop."""

    def __init__(self, batches):
        super().__init__()
        self.batches = list(batches)
        self.offsets = []

    async def _call(self, method, **payload):
        self.calls.append((method, payload))
        if method != "getUpdates":
            return {}
        self.offsets.append(payload["offset"])
        if not self.batches:
            raise asyncio.CancelledError
        return self.batches.pop(0)


async def test_polling_ingests_updates_and_advances_the_offset(engine):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    bot = PollingBot([[update(text="/start", update_id=7), update(action="book", update_id=8)]])

    with pytest.raises(asyncio.CancelledError):
        await poll_updates(bot, sessions)

    # Telegram refuses getUpdates while a webhook is registered.
    assert [method for method, _ in bot.calls][0] == "deleteWebhook"
    # Starts from a clean inbox, then acknowledges only past the batch it stored.
    assert bot.offsets == [1, 9]
    async with sessions() as session:
        stored = list((await session.scalars(select(TelegramUpdate).order_by(TelegramUpdate.update_id))).all())
    assert [row.update_id for row in stored] == [7, 8]
    assert stored[0].payload["message"]["text"] == "/start"
    assert all(row.processed_at is None and row.attempts == 0 for row in stored)


async def test_polling_resumes_after_stored_updates_and_ignores_replays(engine):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(TelegramUpdate(update_id=42, payload=update(text="/start", update_id=42)))
        await session.commit()

    # Telegram replaying an already-stored update must not duplicate the inbox row.
    bot = PollingBot([[update(text="/help", update_id=42), update(text="/tickets", update_id=43)]])
    with pytest.raises(asyncio.CancelledError):
        await poll_updates(bot, sessions)

    assert bot.offsets == [43, 44]
    async with sessions() as session:
        stored = list((await session.scalars(select(TelegramUpdate).order_by(TelegramUpdate.update_id))).all())
    assert [row.update_id for row in stored] == [42, 43]
    assert stored[0].payload["message"]["text"] == "/start"
