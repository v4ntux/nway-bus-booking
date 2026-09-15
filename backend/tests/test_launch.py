"""Launch features: languages, FAQ, support relay, inline mode, reminders, booking privacy."""
import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.models import Reservation
from app.models.faq import FaqItem
from app.models.telegram import TelegramChat, TelegramDelivery, TelegramSupportMessage
from app.services.faq import ensure_default_faq
from app.services.telegram_worker import deliver_one
from app.utils.startapp import decode_uuid, route_param
from app.utils.time import utcnow
from tests.test_telegram import FakeTelegram, prepare_checkout, update

BOT_TOKEN = "123456:test-token"


def init_data(chat_id, token=BOT_TOKEN):
    fields = {"auth_date": str(int(time.time())), "query_id": "AAE", "user": json.dumps({"id": chat_id, "first_name": "Ali"})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def last_text(bot):
    return next(p["text"] for m, p in reversed(bot.calls) if "text" in p)


def callbacks(bot):
    return [b.get("callback_data", "") for m, p in bot.calls for row in p.get("reply_markup", {}).get("inline_keyboard", []) for b in row]


async def test_language_follows_client_and_can_be_switched(engine, world):
    bot = FakeTelegram()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        await bot.handle_update(update(text="/start", lang="ru"), session)
    assert "Добро пожаловать" in bot.calls[0][1]["text"]
    assert "ваша дорога" in last_text(bot)
    async with sessions() as session:
        await bot.handle_update(update(action="lang", lang="ru", update_id=2), session)
    assert "yo‘lingiz" in last_text(bot)
    async with sessions() as session:
        assert (await session.get(TelegramChat, 4242)).lang == "uz"
        await bot.handle_update(update(text="/start", chat_id=5151, lang="uz"), session)
    assert "xush kelibsiz" in bot.calls[-2][1]["text"]


async def test_faq_menu_lists_questions_and_opens_answer(engine, world):
    bot = FakeTelegram()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        assert await ensure_default_faq(session) > 0
        assert await ensure_default_faq(session) == 0  # never re-seeds edited content
        await bot.handle_update(update(text="/faq", lang="ru"), session)
    faq_buttons = [data for data in callbacks(bot) if data.startswith("fq:")]
    assert faq_buttons
    async with sessions() as session:
        item = await session.get(FaqItem, __import__("uuid").UUID(faq_buttons[0][3:]))
        assert item.lang == "ru"
        await bot.handle_update(update(action=faq_buttons[0], lang="ru", update_id=2), session)
    assert item.question in last_text(bot)


async def test_support_relays_passenger_and_operator_messages(engine, world, monkeypatch):
    group = -1001234567890
    monkeypatch.setattr(get_settings(), "TELEGRAM_SUPPORT_CHAT_ID", group)
    bot = FakeTelegram()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        await bot.handle_update(update(action="support", lang="ru"), session)
    async with sessions() as session:
        assert (await session.get(TelegramChat, 4242)).data["stage"] == "support"
        await bot.handle_update(update(text="Где посадка?", lang="ru", update_id=2), session)
    card = next(p for m, p in bot.calls if m == "sendMessage" and p["chat_id"] == group)
    assert "<code>4242</code>" in card["text"]
    copy = next(p for m, p in bot.calls if m == "copyMessage")
    assert copy["chat_id"] == group and copy["from_chat_id"] == 4242
    async with sessions() as session:
        links = list((await session.scalars(select(TelegramSupportMessage))).all())
        assert len(links) == 2 and {link.chat_id for link in links} == {4242}
        copied_id = max(link.group_message_id for link in links)
        # A follow-up within the thread window reuses the thread instead of a new card.
        await bot.handle_update(update(text="И багаж?", lang="ru", update_id=3), session)
    assert len([p for m, p in bot.calls if m == "sendMessage" and p["chat_id"] == group]) == 1

    operator_reply = {"update_id": 4, "message": {
        "message_id": 900, "chat": {"id": group, "type": "supergroup"}, "from": {"id": 77, "first_name": "Operator"},
        "text": "Посадка у 3-й платформы", "reply_to_message": {"message_id": copied_id}}}
    async with sessions() as session:
        await bot.handle_update(operator_reply, session)
    answer = next(p for m, p in reversed(bot.calls) if m == "sendMessage" and p["chat_id"] == 4242)
    assert "Ответ поддержки" in answer["text"] and "3-й платформы" in answer["text"]

    stranger_reply = {**operator_reply, "update_id": 5, "message": {**operator_reply["message"], "message_id": 901, "reply_to_message": {"message_id": 424242}}}
    count = len(bot.calls)
    async with sessions() as session:
        await bot.handle_update(stranger_reply, session)
    assert len(bot.calls) == count  # unrelated group chatter is ignored


async def test_support_without_group_shows_contact_and_stays_out_of_relay(engine, world, monkeypatch):
    monkeypatch.setattr(get_settings(), "TELEGRAM_SUPPORT_CHAT_ID", 0)
    monkeypatch.setattr(get_settings(), "TELEGRAM_SUPPORT", "+998 71 000 00 00")
    bot = FakeTelegram()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        await bot.handle_update(update(text="/support"), session)
    assert "+998 71 000 00 00" in last_text(bot)
    async with sessions() as session:
        assert (await session.get(TelegramChat, 4242)).data.get("stage") is None


async def test_inline_query_offers_routes_with_mini_app_links(engine, world):
    bot = FakeTelegram()
    bot.username = "nway_test_bot"
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    query = {"update_id": 1, "inline_query": {"id": "q1", "from": {"id": 4242, "language_code": "ru"}, "query": "ташк"}}
    async with sessions() as session:
        await bot.handle_update(query, session)
    method, payload = bot.calls[-1]
    assert method == "answerInlineQuery" and len(payload["results"]) == 1
    url = payload["results"][0]["reply_markup"]["inline_keyboard"][0][0]["url"]
    param = url.split("startapp=")[1]
    assert param == route_param(world["origin"].id, world["dest"].id) and len(param) <= 64
    assert decode_uuid(param[1:23]) == world["origin"].id
    async with sessions() as session:
        await bot.handle_update({**query, "inline_query": {**query["inline_query"], "query": "самарканд"}}, session)
    assert bot.calls[-1][1]["results"] == []


async def test_reminder_is_sent_once_before_departure(engine, world):
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    async with sessions() as session:
        booking = await session.scalar(select(Reservation))
        booking.created_at = utcnow() - timedelta(days=2)
        trip = await session.get(type(world["trip"]), booking.trip_id)
        trip.departure_datetime = utcnow() + timedelta(minutes=90)
        await session.commit()
        assert await bot.send_reminders(session) == 1
        assert await bot.send_reminders(session) == 0
    reminders = [p for m, p in bot.calls if m == "sendMessage" and "view:" in json.dumps(p.get("reply_markup", {})) and "<code>" in p["text"]]
    assert reminders and booking.public_code in reminders[-1]["text"]


async def test_web_booking_requires_contact_phone(client, world):
    trip, seat = world["trip"], world["seats"][0]
    created = await client.post("/api/v1/reservations", json={
        "trip_id": str(trip.id), "seat_ids": [str(seat.id)], "contact_phone": "+998901234567",
        "passengers": [{"seat_id": str(seat.id), "first_name": "Ali"}]})
    assert created.status_code == 201
    code = created.json()["public_code"]
    assert (await client.get(f"/api/v1/reservations/{code}")).status_code == 404
    assert (await client.post(f"/api/v1/reservations/{code}/confirm-cash")).status_code == 404
    assert (await client.post(f"/api/v1/reservations/{code}/cancel", headers={"X-Booking-Phone": "+998900000000"})).status_code == 404
    owner = {"X-Booking-Phone": "+998 90 123 45 67"}
    assert (await client.get(f"/api/v1/reservations/{code}", headers=owner)).status_code == 200
    assert (await client.post(f"/api/v1/reservations/{code}/confirm-cash", headers=owner)).json()["status"] == "confirmed"
    assert (await client.get(f"/api/v1/reservations/{code}/tickets", headers=owner)).status_code == 200
    lookup = await client.post("/api/v1/bookings/lookup", json={"phone": "+998901234567", "public_code": code})
    assert lookup.status_code == 200
    assert (await client.post(f"/api/v1/reservations/{code}/cancel", headers=owner)).json()["status"] == "cancelled"


async def test_mini_app_lists_and_resends_own_bookings(client, engine, world, monkeypatch):
    monkeypatch.setattr(get_settings(), "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    bot = FakeTelegram()
    send, nonce, sessions = await prepare_checkout(bot, engine, world)
    await send(action=f"ok:{nonce}")
    assert (await client.get("/api/v1/me/reservations")).status_code == 401
    mine = await client.get("/api/v1/me/reservations", headers={"X-Telegram-Init-Data": init_data(4242)})
    assert mine.status_code == 200
    [item] = mine.json()
    assert item["trip"]["origin_city"] == world["origin"].name and item["can_cancel"] is True
    assert len(item["tickets"]) == 1 and item["tickets"][0]["status"] == "valid"
    stranger = await client.get("/api/v1/me/reservations", headers={"X-Telegram-Init-Data": init_data(9999)})
    assert stranger.json() == []

    code = item["public_code"]
    assert await deliver_one(bot, sessions)
    denied = await client.post(f"/api/v1/reservations/{code}/telegram-resend", headers={"X-Telegram-Init-Data": init_data(9999)})
    assert denied.status_code == 404
    resent = await client.post(f"/api/v1/reservations/{code}/telegram-resend", headers={"X-Telegram-Init-Data": init_data(4242)})
    assert resent.status_code == 202
    async with sessions() as session:
        assert (await session.scalar(select(TelegramDelivery))).sent_at is None


async def test_faq_is_public_and_managed_by_admins(client, world):
    login = await client.post("/api/v1/auth/admin/login", json={"email": "admin@example.com", "password": "secret"})
    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
    body = {"lang": "ru", "category": "trip", "question": "Можно с собакой?", "answer": "Только в переноске.", "position": 1}
    assert (await client.post("/api/v1/admin/faq", json=body)).status_code == 401
    created = await client.post("/api/v1/admin/faq", json=body, headers=auth)
    assert created.status_code == 201
    item_id = created.json()["id"]
    public = await client.get("/api/v1/faq", params={"lang": "ru"})
    assert [f["question"] for f in public.json()] == ["Можно с собакой?"]
    assert (await client.get("/api/v1/faq", params={"lang": "uz"})).json() == []
    hidden = await client.patch(f"/api/v1/admin/faq/{item_id}", json={**body, "active": False}, headers=auth)
    assert hidden.json()["active"] is False
    assert (await client.get("/api/v1/faq", params={"lang": "ru"})).json() == []
    assert (await client.delete(f"/api/v1/admin/faq/{item_id}", headers=auth)).status_code == 204
    assert (await client.delete(f"/api/v1/admin/faq/{uuid4()}", headers=auth)).status_code == 404
    config = (await client.get("/api/v1/app-config")).json()
    assert {"bot_username", "support_contact", "support_chat"} <= config.keys()


async def test_contact_shared_from_mini_app_is_saved_quietly(engine, world):
    bot = FakeTelegram()
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(TelegramChat(chat_id=4242, lang="uz", data={}))
        await session.commit()
        await bot.handle_update(update(contact={"user_id": 4242, "phone_number": "998901234567"}), session)
    assert bot.calls == []
    async with sessions() as session:
        assert (await session.get(TelegramChat, 4242)).phone == "+998901234567"
        assert await session.scalar(select(func.count()).select_from(Reservation)) == 0
