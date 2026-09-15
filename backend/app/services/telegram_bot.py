"""Inline bookings, durable conversations, and real PNG tickets."""
from __future__ import annotations

import asyncio
import html
import json
import logging
import secrets
from datetime import date, timedelta
from uuid import UUID
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models import City, PaymentMethod, PaymentStatus, Reservation, ReservationStatus, Route, Seat, Ticket, TicketStatus, Trip
from app.models.telegram import TelegramChat, TelegramDelivery
from app.services.reservation import PassengerInput, ReservationService, SeatMapService
from app.services.ticket import TicketService
from app.services.ticket_image import TicketImageData, render_ticket
from app.services.trip import TripService
from app.utils.phone import normalize_phone
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
COMMANDS = [
    {"command": "start", "description": "Bosh menyu"},
    {"command": "book", "description": "Reys va joy tanlash"},
    {"command": "tickets", "description": "Chiptalarim"},
    {"command": "help", "description": "Yordam va safar qoidalari"},
    {"command": "admin", "description": "Xodimlar paneli"},
]


def button(text, data):
    if len(data.encode()) > 64:
        raise ValueError("Telegram callback exceeds 64 bytes")
    return {"text": text, "callback_data": data}


def keyboard(*rows):
    return {"inline_keyboard": list(rows)}


def money(minor, currency="UZS"):
    amount, cents = divmod(minor, 100)
    value = f"{amount:,}".replace(",", " ") + (f",{cents:02d}" if cents else "")
    return f"{value} {'so‘m' if currency == 'UZS' else currency}"


def esc(value):
    return html.escape(str(value or ""))


class TelegramAPIError(Exception):
    def __init__(self, method, code, retry_after=0):
        super().__init__(f"Telegram {method}: error {code}")
        self.code, self.retry_after = code, retry_after


class TelegramBotClient:
    def __init__(self, token, webapp_url="", *, client=None):
        self.token = token
        candidate = (webapp_url or get_settings().TELEGRAM_WEBAPP_URL).rstrip("/")
        parts = urlsplit(candidate)
        self.webapp_url = candidate if parts.scheme == "https" and parts.netloc else ""
        if candidate and not self.webapp_url:
            # Telegram only opens Mini Apps over HTTPS; without it the bot silently
            # loses every web_app button, so say so loudly.
            logger.warning(
                "telegram_webapp_disabled reason=not_https url_scheme=%s — "
                "set TELEGRAM_WEBAPP_URL to an HTTPS origin (tunnel or deployed frontend)",
                parts.scheme or "none")
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(40, connect=10))

    async def close(self):
        await self.client.aclose()

    async def _call(self, method, **payload):
        photo = payload.pop("_photo", None)
        try:
            url = f"https://api.telegram.org/bot{self.token}/{method}"
            if photo is not None:
                form = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v) for k, v in payload.items()}
                response = await self.client.post(url, data=form, files={"photo": ("nway-ticket.png", photo, "image/png")})
            else:
                response = await self.client.post(url, json=payload)
            result = response.json()
        except (httpx.HTTPError, ValueError):
            raise TelegramAPIError(method, 0) from None
        if not result.get("ok"):
            raise TelegramAPIError(method, int(result.get("error_code", response.status_code)), int(result.get("parameters", {}).get("retry_after", 0)))
        return result.get("result")

    async def setup(self):
        identity = await self._call("getMe")
        self.username = identity["username"]
        await self._call("setMyCommands", commands=COMMANDS)
        await self._call("setChatMenuButton", menu_button=(
            {"type": "web_app", "text": "📱 NWay", "web_app": {"url": self.webapp_url}}
            if self.webapp_url else {"type": "commands"}))
        await self._call("setMyShortDescription", short_description="🚌 NWay — yo‘lingizni tanlang. Joy band qiling va QR-chiptani Telegramda oling.")
        logger.info("telegram_bot_configured")

    async def screen(self, chat_id, text, markup=None, message_id=None):
        payload = dict(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=markup or keyboard([button("⌂ Bosh menyu", "home")]))
        if message_id:
            try:
                return await self._call("editMessageText", message_id=message_id, **payload)
            except TelegramAPIError as error:
                if error.code != 400:
                    raise
        return await self._call("sendMessage", **payload)

    async def save(self, session, chat, **data):
        chat.data = {**chat.data, **data}
        await session.commit()

    def web_button(self, label, path=""):
        return {"text": label, "web_app": {"url": self.webapp_url + path}}

    async def open_app(self, session, chat, message_id=None):
        if not getattr(self, "webapp_url", ""):
            return await self.origins(session, chat, message_id)
        await self.screen(chat.chat_id,
            "🎫 <b>Qayerga boramiz?</b>\n\nYo‘nalish → sana → qulay joy → tasdiqlash.\n"
            "Chipta rasmini shu chatga yuboramiz. 💌\n\n💵 To‘lov — avtobusga chiqishda.",
            keyboard([self.web_button("🎫 Chipta sotib olish", "/book")],
                     [self.web_button("📱 Ilovani ochish")],
                     [button("🏠 Bosh menyu", "home")]), message_id)

    async def home(self, session, chat, message_id=None):
        chat.data = {}
        await session.commit()
        demo = "\n\n🧪 <b>Sinov rejimi.</b> Reyslar namuna uchun. Pul yechilmaydi, chipta haqiqiy safar uchun yaroqsiz." if get_settings().TELEGRAM_DEMO_MODE else ""
        rows = ([self.web_button("🎫 Chipta sotib olish", "/book")],
                [self.web_button("📱 Ilovani ochish")]) if getattr(self, "webapp_url", "") else ([button("🎫 Reys topish", "book")],)
        await self.screen(chat.chat_id,
            "🚌 <b>NWay — yo‘lingiz shu yerdan boshlanadi!</b>\n\n"
            "Assalomu alaykum! 👋\nQulay joy, oson bron va barcha chiptalaringiz bir joyda.\n\n"
            "🗺 Yo‘nalish va sanani tanlang\n💺 Avtobusdan joyingizni belgilang\n🎫 QR-chiptani rasm ko‘rinishida oling\n\n"
            "💵 To‘lov — avtobusga chiqishda" + demo,
            keyboard(*rows, [button("🧾 Chiptalarim", "mine"), button("💬 Yordam", "help")]), message_id)

    async def origins(self, session, chat, message_id=None):
        cities = list((await session.scalars(select(City).join(Route, Route.origin_city_id == City.id).where(City.active.is_(True), Route.active.is_(True)).distinct().order_by(City.name))).all())
        chat.data = {"stage": "origin", "nonce": secrets.token_hex(6)}
        await session.commit()
        buttons = [button(c.name, f"o:{c.id}") for c in cities]
        await self.screen(chat.chat_id, "<b>1 / 5 · Маршрут</b>\n\nОткуда поедем?", keyboard(*[buttons[i:i+2] for i in range(0, len(buttons), 2)], [button("⌂ Bosh menyu", "home")]), message_id)

    async def destinations(self, session, chat, origin_id, message_id=None):
        origin = await session.get(City, UUID(origin_id))
        if not origin or not origin.active:
            raise DomainError("CITY_NOT_FOUND", "Город не найден")
        cities = list((await session.scalars(select(City).join(Route, Route.destination_city_id == City.id).where(Route.origin_city_id == origin.id, Route.active.is_(True), City.active.is_(True)).distinct().order_by(City.name))).all())
        await self.save(session, chat, stage="destination", origin=str(origin.id), destination=None, trip=None, seat=None, nonce=secrets.token_hex(6))
        buttons = [button(c.name, f"d:{c.id}") for c in cities]
        await self.screen(chat.chat_id, f"<b>1 / 5 · Маршрут</b>\n\n📍 Из {esc(origin.name)}\nКуда отправимся?", keyboard(*[buttons[i:i+2] for i in range(0, len(buttons), 2)], [button("← Назад", "book")]), message_id)

    async def dates(self, session, chat, destination_id, message_id=None):
        origin_id = chat.data.get("origin")
        if not origin_id:
            return await self.origins(session, chat, message_id)
        route = await session.scalar(select(Route).where(Route.origin_city_id == UUID(origin_id), Route.destination_city_id == UUID(destination_id), Route.active.is_(True)))
        if not route:
            raise DomainError("ROUTE_NOT_FOUND", "На этом направлении пока нет рейсов")
        origin = await session.get(City, UUID(origin_id))
        destination = await session.get(City, UUID(destination_id))
        await self.save(session, chat, stage="date", destination=destination_id, trip=None, seat=None)
        today = utcnow().astimezone(ZoneInfo(origin.timezone)).date()
        buttons = []
        weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        for offset in range(10):
            day = today + timedelta(days=offset)
            title = "Сегодня" if offset == 0 else "Завтра" if offset == 1 else weekdays[day.weekday()]
            buttons.append(button(f"{title} · {day:%d.%m}", f"dt:{day.isoformat()}"))
        await self.screen(chat.chat_id, f"<b>2 / 5 · Дата поездки</b>\n\n{esc(origin.name)} → {esc(destination.name)}\n\nКогда хотите поехать?", keyboard(*[buttons[i:i+2] for i in range(0, len(buttons), 2)], [button("← Направления", f"o:{origin_id}")]), message_id)

    async def trips(self, session, chat, day_text, message_id=None):
        if not chat.data.get("destination"):
            return await self.origins(session, chat, message_id)
        day = date.fromisoformat(day_text)
        origin = await session.get(City, UUID(chat.data["origin"]))
        today = utcnow().astimezone(ZoneInfo(origin.timezone)).date()
        if day < today or day > today + timedelta(days=9):
            return await self.dates(session, chat, chat.data["destination"], message_id)
        found = await TripService(session).search(UUID(chat.data["origin"]), UUID(chat.data["destination"]), day)
        cutoff = utcnow() + timedelta(minutes=get_settings().TELEGRAM_BOOKING_CUTOFF_MINUTES)
        found = [row for row in found if row["available_seats"] > 0 and row["trip"].departure_datetime > cutoff]
        await self.save(session, chat, stage="trip", day=day_text, trip=None, seat=None, trips=[str(r["trip"].id) for r in found[:20]])
        buttons = []
        for row in found[:20]:
            trip = row["trip"]
            local = trip.departure_datetime.astimezone(ZoneInfo(origin.timezone))
            buttons.append([button(f"{local:%H:%M} · {money(trip.base_price_minor, trip.currency)} · {row['available_seats']} мест", f"tr:{trip.id}")])
        text = f"<b>3 / 5 · Рейс</b>\n\n📅 {day:%d.%m.%Y}\n"
        text += "Выберите время отправления. Цена указана за одного пассажира." if found else "На эту дату свободных рейсов нет. Выберите другой день."
        await self.screen(chat.chat_id, text, keyboard(*buttons, [button("← Другая дата", f"d:{chat.data['destination']}")]), message_id)

    async def seats(self, session, chat, trip_id, message_id=None):
        if trip_id not in chat.data.get("trips", []):
            raise DomainError("STALE_BUTTON", "Выберите рейс заново")
        trip = await TripService(session).get(UUID(trip_id))
        seat_map = await SeatMapService(session).trip_seat_map(trip.id)
        chosen = chat.data.get("seat") if chat.data.get("trip") == trip_id else None
        rows = []
        for row_no in sorted({cell["row"] for cell in seat_map["cells"]}):
            row = []
            for cell in sorted((c for c in seat_map["cells"] if c["row"] == row_no), key=lambda c: c["column"]):
                seat = cell["seat"]
                if seat:
                    available = seat["status"] == "available" and seat["type"] != "blocked"
                    selected = str(seat["id"]) == chosen
                    mark = "✅" if selected and available else "▫️" if available else "✖️"
                    if seat.get("is_women_only") and available and not selected:
                        mark = "🌸"
                    row.append(button(f"{mark} {seat['seat_number']}", f"s:{seat['id']}" if available else "unavailable"))
                else:
                    row.append(button("▸" if cell["cell_type"] == "driver" else "·", "noop"))
            if row:
                rows.append(row[:8])
        await self.save(session, chat, stage="seat", trip=trip_id, seat=chosen)
        local = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        text = f"<b>4 / 5 · Ваше место</b>\n\n{esc(trip.route.origin_city.name)} → {esc(trip.route.destination_city.name)}\n📅 {local:%d.%m, %H:%M} · {money(trip.base_price_minor, trip.currency)}\n\n▫️ Свободно · ✖️ Занято · ✅ Выбрано\n🌸 Место для пассажирки\n\nВыберите одно место на схеме. Бронь создаётся после подтверждения заказа."
        if chosen:
            rows.append([button("Продолжить →", "passenger")])
        rows.append([button("← Другой рейс", f"dt:{chat.data['day']}")])
        await self.screen(chat.chat_id, text, keyboard(*rows), message_id)

    async def choose_seat(self, session, chat, seat_id, message_id=None):
        if chat.data.get("stage") != "seat" or not chat.data.get("trip"):
            raise DomainError("STALE_BUTTON", "Откройте выбор места заново")
        trip = await session.get(Trip, UUID(chat.data["trip"]))
        seat = await session.get(Seat, UUID(seat_id))
        if not seat or seat.bus_id != trip.bus_id:
            raise DomainError("SEAT_WRONG_BUS", "Это место относится к другому автобусу")
        await self.save(session, chat, seat=None if chat.data.get("seat") == seat_id else seat_id)
        await self.seats(session, chat, str(trip.id), message_id)

    async def passenger(self, session, chat, sender, message_id=None):
        if not chat.data.get("seat"):
            raise DomainError("NO_SEATS", "Сначала выберите место")
        if not chat.phone:
            await self.save(session, chat, stage="phone")
            return await self._call("sendMessage", chat_id=chat.chat_id, parse_mode="HTML",
                text="<b>5 / 5 · Пассажир</b>\n\nПоделитесь своим номером кнопкой ниже. Он нужен для связи по поездке. Чужие контакты не принимаются.\n\n/start — вернуться в меню",
                reply_markup={"keyboard": [[{"text": "📱 Поделиться моим номером", "request_contact": True}]], "resize_keyboard": True, "one_time_keyboard": True})
        suggested = " ".join(str(sender.get(k) or "") for k in ("first_name", "last_name")).strip()[:100]
        await self.save(session, chat, stage="name", suggested_name=suggested)
        rows = [[button(f"✓ {suggested[:35]}", "nameok")]] if suggested else []
        rows.append([button("← Выбор места", f"tr:{chat.data['trip']}")])
        await self.screen(chat.chat_id, "<b>5 / 5 · Пассажир</b>\n\nКак указать имя в билете?\nПодтвердите имя из Telegram или напишите имя и фамилию одним сообщением.", keyboard(*rows), message_id)

    async def review(self, session, chat, name, message_id=None):
        name = " ".join(name.split())
        if not name or len(name) > 100:
            raise DomainError("INVALID_NAME", "Введите имя и фамилию, до 100 символов")
        if not chat.phone or not chat.data.get("trip") or not chat.data.get("seat"):
            raise DomainError("STALE_BUTTON", "Начните заказ заново")
        trip = await TripService(session).get(UUID(chat.data["trip"]))
        seat = await session.get(Seat, UUID(chat.data["seat"]))
        await self.save(session, chat, stage="review", passenger=name)
        local = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        demo = "\n\n🧪 Это тестовый рейс. Билет не даёт права проезда." if get_settings().TELEGRAM_DEMO_MODE else ""
        text = (f"<b>Проверьте заказ</b>\n\n🚌 {esc(trip.route.origin_city.name)} → {esc(trip.route.destination_city.name)}"
                f"\n📅 {local:%d.%m.%Y} · {local:%H:%M}\n💺 Joy {esc(seat.seat_number)}\n👤 {esc(name)}\n📱 {esc(chat.phone)}"
                f"\n\n<b>Итого: {money(trip.base_price_minor, trip.currency)}</b>\n💵 To‘lov chiqishda. Сейчас платить не нужно."
                "\n\nПосле подтверждения место будет забронировано, а билет придёт картинкой." + demo)
        await self.screen(chat.chat_id, text, keyboard([button("✅ Подтвердить и получить билет", f"ok:{chat.data['nonce']}")], [button("✏️ Пассажир", "passenger"), button("← Место", f"tr:{trip.id}")], [button("Отменить оформление", "home")]), message_id)

    async def checkout(self, session, chat, nonce, message_id=None):
        key = f"telegram:{chat.chat_id}:{nonce}"
        reservation = await session.scalar(select(Reservation).where(Reservation.booking_request_key == key))
        if not reservation:
            if chat.data.get("stage") != "review" or nonce != chat.data.get("nonce"):
                raise DomainError("STALE_BUTTON", "Этот заказ уже изменён. Начните поиск заново")
            trip = await TripService(session).get(UUID(chat.data["trip"]))
            if trip.departure_datetime <= utcnow() + timedelta(minutes=get_settings().TELEGRAM_BOOKING_CUTOFF_MINUTES):
                raise DomainError("TRIP_DEPARTED", "До отправления осталось слишком мало времени. Выберите другой рейс")
            reservation = await ReservationService(session).create(
                trip_id=trip.id, seat_ids=[UUID(chat.data["seat"])], contact_phone=chat.phone,
                passengers=[PassengerInput(seat_id=UUID(chat.data["seat"]), first_name=chat.data["passenger"])],
                user_id=chat.user_id, booking_request_key=key, telegram_chat_id=chat.chat_id)
        if reservation.telegram_chat_id != chat.chat_id:
            raise DomainError("BOOKING_OWNER_MISMATCH", "Bron topilmadi", 403)
        if reservation.status == ReservationStatus.pending:
            reservation.payment_method = PaymentMethod.cash
            reservation = await ReservationService(session).confirm(reservation.id, actor_id=chat.user_id)
        if reservation.status != ReservationStatus.confirmed:
            raise DomainError("BOOKING_CLOSED", "Этот заказ уже закрыт. Создайте новый")
        await self.queue_tickets(session, reservation, chat.chat_id)
        await self.save(session, chat, stage="complete", reservation_code=reservation.public_code)
        await self.screen(chat.chat_id, f"✅ <b>Готово! Место забронировано.</b>\n\nЗаказ <code>{esc(reservation.public_code)}</code>\nБилет отправляется следующим сообщением. Сохраните картинку.\n\n💵 To‘lov chiqishda — билет не означает, что поездка оплачена.", keyboard([button("🧾 Chiptalarim", "mine")], [button("🎫 Ещё один билет", "book")]), message_id)

    async def queue_tickets(self, session, reservation, chat_id, resend=False):
        tickets = await TicketService(session).list_for_reservation(reservation.id)
        for ticket in tickets:
            if ticket.status != TicketStatus.valid:
                continue
            stmt = insert(TelegramDelivery).values(ticket_id=ticket.id, chat_id=chat_id, attempts=0)
            if resend:
                stmt = stmt.on_conflict_do_update(index_elements=[TelegramDelivery.ticket_id], set_={"sent_at": None, "attempts": 0, "available_at": utcnow(), "last_error": None})
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=[TelegramDelivery.ticket_id])
            await session.execute(stmt)
        await session.commit()

    async def my_tickets(self, session, chat, message_id=None):
        reservations = list((await session.scalars(select(Reservation).where(Reservation.telegram_chat_id == chat.chat_id).order_by(Reservation.created_at.desc()).limit(10))).all())
        rows = []
        for reservation in reservations:
            mark = "✅" if reservation.status == ReservationStatus.confirmed else "✖️" if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired} else "⏳"
            rows.append([button(f"{mark} {reservation.public_code} · {money(reservation.total_amount_minor, reservation.currency)}", f"view:{reservation.public_code}")])
        text = "<b>🧾 Chiptalarim</b>\n\nBronni tanlang. Chiptani qayta oling yoki to‘lanmagan safarni bekor qiling." if reservations else "<b>🧾 Chiptalarim</b>\n\nHozircha chipta yo‘q. Reys tanlang — tasdiqlangan chiptangiz shu yerda paydo bo‘ladi."
        rows.append([button("🎫 Reys topish", "book"), button("🏠 Bosh menyu", "home")])
        await self.screen(chat.chat_id, text, keyboard(*rows), message_id)

    async def owned_booking(self, session, chat, code):
        reservation = await session.scalar(select(Reservation).where(Reservation.public_code == code, Reservation.telegram_chat_id == chat.chat_id))
        if not reservation:
            raise DomainError("RESERVATION_NOT_FOUND", "Bron topilmadi")
        return await ReservationService(session).get_by_id(reservation.id)

    async def show_booking(self, session, chat, code, message_id=None):
        reservation = await self.owned_booking(session, chat, code)
        trip = await TripService(session).get(reservation.trip_id)
        statuses = {"confirmed": "Tasdiqlangan", "cancelled": "Bekor qilingan", "expired": "Muddati tugagan", "completed": "Safar yakunlangan", "no_show": "Kelmadi"}
        status = statuses.get(reservation.status.value, "Tasdiq kutilmoqda")
        local = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        text = f"<b>Bron {esc(code)}</b>\n\n{esc(trip.route.origin_city.name)} → {esc(trip.route.destination_city.name)}\n📅 {local:%d.%m.%Y, %H:%M}\n💺 Joy {esc(', '.join(s.seat.seat_number for s in reservation.seats))}\n\nHolati: <b>{status}</b>\n{money(reservation.total_amount_minor, reservation.currency)} · {'To‘langan' if reservation.payment_status == PaymentStatus.paid else 'To‘lov chiqishda'}"
        rows = []
        if reservation.status == ReservationStatus.confirmed:
            rows.append([button("🖼 Chiptani rasm qilib olish", f"image:{code}")])
            if trip.departure_datetime > utcnow() and reservation.payment_status == PaymentStatus.unpaid:
                rows.append([button("Safarni bekor qilish", f"cancelask:{code}")])
        rows.append([button("← Barcha chiptalar", "mine"), button("🏠 Bosh menyu", "home")])
        await self.screen(chat.chat_id, text, keyboard(*rows), message_id)

    async def handle_update(self, update, session):
        callback = update.get("callback_query")
        message = callback.get("message", {}) if callback else update.get("message", {})
        sender = callback.get("from", {}) if callback else message.get("from", {})
        chat_info = message.get("chat", {})
        if chat_info.get("type") != "private" or chat_info.get("id") != sender.get("id") or sender.get("is_bot"):
            return
        chat_id = int(chat_info["id"])
        chat = await session.get(TelegramChat, chat_id)
        if not chat:
            chat = TelegramChat(chat_id=chat_id, data={})
            session.add(chat)
            await session.commit()
        if callback:
            try:
                await self._call("answerCallbackQuery", callback_query_id=callback["id"])
            except TelegramAPIError as error:
                if error.code != 400:
                    raise
        message_id = message.get("message_id") if callback else None
        try:
            if callback:
                return await self.handle_action(session, chat, sender, callback.get("data", ""), message_id)
            text = (message.get("text") or "").strip()
            command = text.split()[0].split("@")[0].lower() if text else ""
            if command == "/start":
                argument = text.partition(" ")[2]
                if argument.startswith("check_"):
                    from app.services.telegram_admin import check
                    return await check(self, session, chat, argument[6:])
                await self._call("sendMessage", chat_id=chat_id, text="NWay’ga xush kelibsiz! 👋", reply_markup={"remove_keyboard": True})
                return await self.home(session, chat)
            if command == "/book":
                return await self.open_app(session, chat)
            if command in {"/tickets", "/lookup"}:
                return await self.my_tickets(session, chat)
            if command == "/help":
                return await self.help(chat)
            if command == "/admin":
                from app.services.telegram_admin import menu
                return await menu(self, session, chat)
            if command == "/check":
                from app.services.telegram_admin import check
                return await check(self, session, chat, text.partition(" ")[2].strip())
            if message.get("contact"):
                if chat.data.get("stage") not in {"phone", "staff_phone"}:
                    return await self.screen(chat_id, "Raqam bron uchun kerak bo‘ladi. «Reys topish» tugmasini bosing.")
                contact = message["contact"]
                if contact.get("user_id") != sender.get("id"):
                    raise DomainError("CONTACT_NOT_YOURS", "Поделитесь именно своим номером кнопкой под сообщением")
                raw_phone = contact["phone_number"]
                phone = normalize_phone(raw_phone if raw_phone.startswith("+") else "+" + raw_phone)
                user = await ReservationService(session)._get_or_create_user(phone, None)
                chat.phone, chat.user_id = phone, user.id
                await session.commit()
                await self._call("sendMessage", chat_id=chat_id, text="Raqam saqlandi ✓", reply_markup={"remove_keyboard": True})
                if chat.data.get("stage") == "staff_phone":
                    from app.services.telegram_admin import menu
                    return await menu(self, session, chat)
                return await self.passenger(session, chat, sender)
            if chat.data.get("stage") == "name" and text:
                return await self.review(session, chat, text)
            await self.screen(chat_id, "Pastdagi tugmalardan foydalaning yoki bosh menyuni oching.", keyboard([button("⌂ Bosh menyu", "home"), button("🧾 Chiptalarim", "mine")]))
        except (ValueError, KeyError, TypeError):
            await session.rollback()
            await self.screen(chat_id, "Bu tugma eskirgan. Qidiruvni qayta oching — chiptalaringiz saqlangan.", keyboard([button("🎫 Reys topish", "book"), button("🧾 Chiptalarim", "mine")]))
        except DomainError as error:
            await session.rollback()
            messages = {"SEAT_ALREADY_RESERVED": "Это место уже заняли. Выберите другое — новый заказ не создан.", "USER_BLOCKED": "Бронирование для этого аккаунта недоступно. Обратитесь в поддержку.", "RESERVATION_EXPIRED": "Время оформления истекло. Выберите рейс заново.", "TRIP_NOT_BOOKABLE": "Этот рейс больше недоступен.", "SEAT_NOT_BOOKABLE": "Это место недоступно. Выберите другое."}
            text = messages.get(error.code, error.message if any("а" <= ch.lower() <= "я" for ch in error.message) else "Не удалось оформить действие. Проверьте данные или начните поиск заново.")
            await self.screen(chat_id, esc(text), keyboard([button("🎫 Reys topish", "book"), button("🧾 Chiptalarim", "mine")]))

    async def handle_action(self, session, chat, sender, action, message_id):
        name, _, value = action.partition(":")
        if name.startswith("staff"):
            from app.services import telegram_admin
            if name == "staff":
                return await telegram_admin.menu(self, session, chat, message_id)
            if name in {"staffview", "staffpayask", "staffpaid"}:
                return await telegram_admin.booking(self, session, chat, value, message_id, action=name.removeprefix("staff"))
            if name in {"staffticket", "staffboard"}:
                return await telegram_admin.check(self, session, chat, value, message_id, board=name == "staffboard")
        if name == "home":
            return await self.home(session, chat, message_id)
        if name == "book":
            return await self.open_app(session, chat, message_id)
        if name == "o":
            return await self.destinations(session, chat, value, message_id)
        if name == "d":
            return await self.dates(session, chat, value, message_id)
        if name == "dt":
            return await self.trips(session, chat, value, message_id)
        if name == "tr":
            return await self.seats(session, chat, value, message_id)
        if name == "s":
            return await self.choose_seat(session, chat, value, message_id)
        if name == "passenger":
            return await self.passenger(session, chat, sender, message_id)
        if name == "nameok":
            if chat.data.get("stage") != "name":
                raise DomainError("STALE_BUTTON", "Подтвердите данные пассажира заново")
            return await self.review(session, chat, chat.data.get("suggested_name", ""), message_id)
        if name == "ok":
            return await self.checkout(session, chat, value, message_id)
        if name == "mine":
            return await self.my_tickets(session, chat, message_id)
        if name == "view":
            return await self.show_booking(session, chat, value, message_id)
        if name == "image":
            reservation = await self.owned_booking(session, chat, value)
            if reservation.status != ReservationStatus.confirmed:
                raise DomainError("BOOKING_CLOSED", "Этот билет больше не действует")
            await self.queue_tickets(session, reservation, chat.chat_id, resend=True)
            return await self.screen(chat.chat_id, "🖼 Отправляю билет. Он появится отдельным сообщением.", keyboard([button("← К заказу", f"view:{value}")]), message_id)
        if name in {"cancelask", "cancel"}:
            reservation = await self.owned_booking(session, chat, value)
            trip = await session.get(Trip, reservation.trip_id)
            if reservation.payment_status != PaymentStatus.unpaid or trip.departure_datetime <= utcnow():
                raise DomainError("CANCEL_UNAVAILABLE", "Для отмены этого заказа обратитесь в поддержку")
            if name == "cancelask":
                return await self.screen(chat.chat_id, f"<b>Отменить заказ {esc(value)}?</b>\n\nМесто снова станет доступно другим пассажирам. Билет перестанет действовать.", keyboard([button("Да, отменить заказ", f"cancel:{value}")], [button("Сохранить поездку", f"view:{value}")]), message_id)
            if reservation.status not in {ReservationStatus.cancelled, ReservationStatus.expired}:
                await ReservationService(session).cancel(reservation.id, chat.user_id)
            return await self.show_booking(session, chat, value, message_id)
        if name == "help":
            return await self.help(chat, message_id)
        if name in {"noop", "unavailable"}:
            return
        return await self.home(session, chat, message_id)

    async def help(self, chat, message_id=None):
        support = get_settings().TELEGRAM_SUPPORT
        contact = f"\n\n💬 Yordam: {esc(support)}" if support else ""
        await self.screen(chat.chat_id,
            "💬 <b>Qanday foydalaniladi?</b>\n\n"
            "1️⃣ «Chipta sotib olish» tugmasini bosing.\n"
            "2️⃣ Ilovada yo‘nalish, sana va joyni tanlang.\n"
            "3️⃣ Ismingiz va telefon raqamingizni kiriting.\n"
            "4️⃣ Bronni tasdiqlang — QR-chip­ta rasmini shu chatda olasiz.\n\n"
            "💵 To‘lov avtobusga chiqishda. Onlayn to‘lov hali ulanmagan.\n"
            "👥 4 va undan ortiq joyni operator tasdiqlaydi.\n"
            "🕒 Vaqt jo‘nash shahri bo‘yicha. 20 daqiqa oldin keling.\n"
            "🧾 «Chiptalarim» orqali chiptani qayta olish yoki to‘lanmagan bronni bekor qilish mumkin." + contact,
            keyboard([button("🎫 Reys topish", "book"), button("🧾 Chiptalarim", "mine")], [button("🏠 Bosh menyu", "home")]), message_id)

    async def send_ticket(self, session, delivery):
        row = await session.get(Ticket, delivery.ticket_id)
        ticket = await TicketService(session).get_by_public_id(row.public_id)
        if ticket.status != TicketStatus.valid or ticket.reservation.status != ReservationStatus.confirmed:
            return
        if ticket.reservation.telegram_chat_id != delivery.chat_id:
            raise DomainError("BOOKING_OWNER_MISMATCH", "Ticket delivery owner mismatch", 403)
        trip = ticket.trip
        departure = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        arrival = trip.estimated_arrival_datetime.astimezone(ZoneInfo(trip.route.destination_city.timezone))
        qr_value = f"https://t.me/{self.username}?start=check_{ticket.qr_token}" if getattr(self, "username", "") else ticket.qr_token
        data = TicketImageData(
            public_id=ticket.public_id, booking_code=ticket.reservation.public_code, qr_token=qr_value,
            origin=trip.route.origin_city.name, destination=trip.route.destination_city.name,
            departure_date=departure.strftime("%d.%m.%Y"), departure_time=departure.strftime("%H:%M"), arrival_time=arrival.strftime("%d.%m %H:%M"),
            passenger=" ".join(filter(None, [ticket.passenger.first_name, ticket.passenger.last_name])), seat=ticket.seat.seat_number,
            bus=f"{trip.bus.name} · {trip.bus.registration_number}", boarding=trip.boarding_location or "Chiqish joyini tashuvchidan aniqlang",
            price=money(ticket.reservation.total_amount_minor, ticket.reservation.currency),
            payment="To‘langan" if ticket.reservation.payment_status == PaymentStatus.paid else "To‘lov chiqishda", demo=get_settings().TELEGRAM_DEMO_MODE)
        png = await asyncio.to_thread(render_ticket, data)
        await self._call("sendPhoto", chat_id=delivery.chat_id, _photo=png,
            caption=f"🎫 <b>Sizning chiptangiz · {esc(ticket.public_id)}</b>\n{esc(data.origin)} → {esc(data.destination)}\n{data.departure_date}, {data.departure_time} · joy {esc(data.seat)}\n{esc(data.payment)}\n\nRasmni saqlab qo‘ying. Joriy holat — «Chiptalarim» bo‘limida." + ("\n🧪 Sinov chiptasi. Haqiqiy safar uchun yaroqsiz." if data.demo else ""),
            parse_mode="HTML", reply_markup=keyboard([button("Bronni ochish", f"view:{data.booking_code}")], [button("🧾 Barcha chiptalar", "mine")]))


async def run_telegram_bot():
    from app.db.session import SessionLocal, engine
    from app.services.telegram_worker import run_worker
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    if not settings.telegram_polling and not settings.TELEGRAM_WEBHOOK_SECRET:
        raise SystemExit(
            "Webhook mode needs TELEGRAM_WEBHOOK_SECRET. "
            "For local development set TELEGRAM_MODE=polling instead.")
    bot = TelegramBotClient(settings.TELEGRAM_BOT_TOKEN)
    try:
        await run_worker(bot, SessionLocal, engine)
    finally:
        await bot.close()
