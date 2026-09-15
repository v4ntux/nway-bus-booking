"""Inline bookings, durable conversations, and real PNG tickets."""
from __future__ import annotations

import asyncio
import html
import json
import logging
import secrets
from datetime import date, timedelta
from functools import partial
from uuid import UUID
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models import BOOKABLE_TRIP_STATUSES, City, PaymentMethod, PaymentStatus, Reservation, ReservationStatus, Route, Seat, Ticket, TicketStatus, Trip
from app.models.faq import FaqItem
from app.models.telegram import TelegramChat, TelegramSupportMessage
from app.services.faq import list_faq
from app.services.reservation import PassengerInput, ReservationService, SeatMapService, queue_telegram_tickets
from app.services.telegram_i18n import COMMANDS, SHORT_DESCRIPTIONS, WEEKDAYS, detect_lang, has_text, t
from app.services.ticket import TicketService
from app.services.ticket_image import TicketImageData, render_ticket
from app.services.trip import TripService
from app.utils.phone import normalize_phone
from app.utils.startapp import route_param
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
SUPPORT_THREAD_WINDOW = timedelta(minutes=30)


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


def has_cyrillic(value):
    return any("а" <= ch.lower() <= "я" for ch in value)


class TelegramAPIError(Exception):
    def __init__(self, method, code, retry_after=0):
        super().__init__(f"Telegram {method}: error {code}")
        self.code, self.retry_after = code, retry_after


class TelegramBotClient:
    def __init__(self, token, webapp_url="", *, client=None):
        self.token = token
        settings = get_settings()
        self.username = settings.TELEGRAM_BOT_USERNAME.lstrip("@")
        candidate = (webapp_url or settings.TELEGRAM_WEBAPP_URL).rstrip("/")
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
        # Default scope is Uzbek; Russian-language clients get Russian commands.
        for language_code, lang in ((None, "uz"), ("ru", "ru")):
            scope = {"language_code": language_code} if language_code else {}
            await self._call("setMyCommands", commands=COMMANDS[lang], **scope)
            await self._call("setMyShortDescription", short_description=SHORT_DESCRIPTIONS[lang], **scope)
        await self._call("setChatMenuButton", menu_button=(
            {"type": "web_app", "text": "🎫 NWay", "web_app": {"url": self.webapp_url + "/book"}}
            if self.webapp_url else {"type": "commands"}))
        logger.info("telegram_bot_configured")

    @property
    def has_app(self):
        return bool(getattr(self, "webapp_url", ""))

    def tr(self, chat):
        return partial(t, chat.lang or "uz")

    def app_link(self, param=""):
        """t.me link that opens the Main Mini App; works in groups, channels and inline results."""
        return f"https://t.me/{self.username}" + (f"?startapp={param}" if param else "?startapp")

    async def screen(self, chat_id, text, markup=None, message_id=None):
        payload = dict(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=markup or keyboard([button("🏠 Menu", "home")]))
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
        if not self.has_app:
            return await self.origins(session, chat, message_id)
        T = self.tr(chat)
        await self.screen(chat.chat_id, T("open_app"),
            keyboard([self.web_button(T("btn_buy"), "/book")],
                     [self.web_button(T("btn_app"))],
                     [button(T("btn_home"), "home")]), message_id)

    async def home(self, session, chat, message_id=None):
        T = self.tr(chat)
        chat.data = {}
        await session.commit()
        demo = T("demo_home") if get_settings().TELEGRAM_DEMO_MODE else ""
        first = [self.web_button(T("btn_buy"), "/book")] if self.has_app else [button(T("btn_find"), "book")]
        await self.screen(chat.chat_id, T("home") + demo,
            keyboard(first,
                     [button(T("btn_my"), "mine"), button(T("btn_faq"), "faq")],
                     [button(T("btn_support"), "support"), button(T("btn_lang"), "lang")]), message_id)

    async def switch_lang(self, session, chat, message_id=None):
        chat.lang = "ru" if (chat.lang or "uz") == "uz" else "uz"
        await session.commit()
        await self.home(session, chat, message_id)

    async def origins(self, session, chat, message_id=None):
        T = self.tr(chat)
        cities = list((await session.scalars(select(City).join(Route, Route.origin_city_id == City.id).where(City.active.is_(True), Route.active.is_(True)).distinct().order_by(City.name))).all())
        chat.data = {"stage": "origin", "nonce": secrets.token_hex(6)}
        await session.commit()
        buttons = [button(c.name, f"o:{c.id}") for c in cities]
        await self.screen(chat.chat_id, T("origin"), keyboard(*[buttons[i:i+2] for i in range(0, len(buttons), 2)], [button(T("btn_home"), "home")]), message_id)

    async def destinations(self, session, chat, origin_id, message_id=None):
        T = self.tr(chat)
        origin = await session.get(City, UUID(origin_id))
        if not origin or not origin.active:
            raise DomainError("CITY_NOT_FOUND", "City not found")
        cities = list((await session.scalars(select(City).join(Route, Route.destination_city_id == City.id).where(Route.origin_city_id == origin.id, Route.active.is_(True), City.active.is_(True)).distinct().order_by(City.name))).all())
        await self.save(session, chat, stage="destination", origin=str(origin.id), destination=None, trip=None, seat=None, nonce=secrets.token_hex(6))
        buttons = [button(c.name, f"d:{c.id}") for c in cities]
        await self.screen(chat.chat_id, T("destination", origin=esc(origin.name)), keyboard(*[buttons[i:i+2] for i in range(0, len(buttons), 2)], [button(T("btn_back"), "book")]), message_id)

    async def dates(self, session, chat, destination_id, message_id=None):
        T = self.tr(chat)
        origin_id = chat.data.get("origin")
        if not origin_id:
            return await self.origins(session, chat, message_id)
        route = await session.scalar(select(Route).where(Route.origin_city_id == UUID(origin_id), Route.destination_city_id == UUID(destination_id), Route.active.is_(True)))
        if not route:
            raise DomainError("ROUTE_NOT_FOUND", "No trips on this route")
        origin = await session.get(City, UUID(origin_id))
        destination = await session.get(City, UUID(destination_id))
        await self.save(session, chat, stage="date", destination=destination_id, trip=None, seat=None)
        today = utcnow().astimezone(ZoneInfo(origin.timezone)).date()
        weekdays = WEEKDAYS[chat.lang or "uz"]
        buttons = []
        for offset in range(10):
            day = today + timedelta(days=offset)
            title = T("today") if offset == 0 else T("tomorrow") if offset == 1 else weekdays[day.weekday()]
            buttons.append(button(f"{title} · {day:%d.%m}", f"dt:{day.isoformat()}"))
        await self.screen(chat.chat_id, T("date", origin=esc(origin.name), destination=esc(destination.name)), keyboard(*[buttons[i:i+2] for i in range(0, len(buttons), 2)], [button(T("btn_directions"), f"o:{origin_id}")]), message_id)

    async def trips(self, session, chat, day_text, message_id=None):
        T = self.tr(chat)
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
            label = T("trip_row", time=f"{local:%H:%M}", price=money(trip.base_price_minor, trip.currency), seats=row["available_seats"])
            buttons.append([button(label, f"tr:{trip.id}")])
        text = T("trips", day=f"{day:%d.%m.%Y}") + (T("trips_found") if found else T("trips_none"))
        await self.screen(chat.chat_id, text, keyboard(*buttons, [button(T("btn_other_date"), f"d:{chat.data['destination']}")]), message_id)

    async def seats(self, session, chat, trip_id, message_id=None):
        T = self.tr(chat)
        if trip_id not in chat.data.get("trips", []):
            raise DomainError("STALE_BUTTON", "Choose the trip again")
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
        text = T("seats", origin=esc(trip.route.origin_city.name), destination=esc(trip.route.destination_city.name),
                 when=f"{local:%d.%m, %H:%M}", price=money(trip.base_price_minor, trip.currency))
        if chosen:
            rows.append([button(T("btn_continue"), "passenger")])
        rows.append([button(T("btn_other_trip"), f"dt:{chat.data['day']}")])
        await self.screen(chat.chat_id, text, keyboard(*rows), message_id)

    async def choose_seat(self, session, chat, seat_id, message_id=None):
        if chat.data.get("stage") != "seat" or not chat.data.get("trip"):
            raise DomainError("STALE_BUTTON", "Open seat selection again")
        trip = await session.get(Trip, UUID(chat.data["trip"]))
        seat = await session.get(Seat, UUID(seat_id))
        if not seat or seat.bus_id != trip.bus_id:
            raise DomainError("SEAT_WRONG_BUS", "Seat belongs to another bus")
        await self.save(session, chat, seat=None if chat.data.get("seat") == seat_id else seat_id)
        await self.seats(session, chat, str(trip.id), message_id)

    async def passenger(self, session, chat, sender, message_id=None):
        T = self.tr(chat)
        if not chat.data.get("seat"):
            raise DomainError("NO_SEATS", "Choose a seat first")
        if not chat.phone:
            await self.save(session, chat, stage="phone")
            return await self._call("sendMessage", chat_id=chat.chat_id, parse_mode="HTML", text=T("phone_request"),
                reply_markup={"keyboard": [[{"text": T("btn_share_phone"), "request_contact": True}]], "resize_keyboard": True, "one_time_keyboard": True})
        suggested = " ".join(str(sender.get(k) or "") for k in ("first_name", "last_name")).strip()[:100]
        await self.save(session, chat, stage="name", suggested_name=suggested)
        rows = [[button(f"✓ {suggested[:35]}", "nameok")]] if suggested else []
        rows.append([button(T("btn_seat_back"), f"tr:{chat.data['trip']}")])
        await self.screen(chat.chat_id, T("name_prompt"), keyboard(*rows), message_id)

    async def review(self, session, chat, name, message_id=None):
        T = self.tr(chat)
        name = " ".join(name.split())
        if not name or len(name) > 100:
            raise DomainError("INVALID_NAME", "Name must be 1-100 characters")
        if not chat.phone or not chat.data.get("trip") or not chat.data.get("seat"):
            raise DomainError("STALE_BUTTON", "Start the order again")
        trip = await TripService(session).get(UUID(chat.data["trip"]))
        seat = await session.get(Seat, UUID(chat.data["seat"]))
        await self.save(session, chat, stage="review", passenger=name)
        local = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        text = T("review", origin=esc(trip.route.origin_city.name), destination=esc(trip.route.destination_city.name),
                 date=f"{local:%d.%m.%Y}", time=f"{local:%H:%M}", seat=esc(seat.seat_number), name=esc(name),
                 phone=esc(chat.phone), price=money(trip.base_price_minor, trip.currency))
        if get_settings().TELEGRAM_DEMO_MODE:
            text += T("demo_review")
        await self.screen(chat.chat_id, text, keyboard(
            [button(T("btn_confirm"), f"ok:{chat.data['nonce']}")],
            [button(T("btn_edit_passenger"), "passenger"), button(T("btn_seat_short"), f"tr:{trip.id}")],
            [button(T("btn_abort"), "home")]), message_id)

    async def checkout(self, session, chat, nonce, message_id=None):
        T = self.tr(chat)
        key = f"telegram:{chat.chat_id}:{nonce}"
        reservation = await session.scalar(select(Reservation).where(Reservation.booking_request_key == key))
        if not reservation:
            if chat.data.get("stage") != "review" or nonce != chat.data.get("nonce"):
                raise DomainError("STALE_BUTTON", "Order changed; start again")
            trip = await TripService(session).get(UUID(chat.data["trip"]))
            if trip.departure_datetime <= utcnow() + timedelta(minutes=get_settings().TELEGRAM_BOOKING_CUTOFF_MINUTES):
                raise DomainError("TRIP_DEPARTED", "Too close to departure")
            reservation = await ReservationService(session).create(
                trip_id=trip.id, seat_ids=[UUID(chat.data["seat"])], contact_phone=chat.phone,
                passengers=[PassengerInput(seat_id=UUID(chat.data["seat"]), first_name=chat.data["passenger"])],
                user_id=chat.user_id, booking_request_key=key, telegram_chat_id=chat.chat_id)
        if reservation.telegram_chat_id != chat.chat_id:
            raise DomainError("BOOKING_OWNER_MISMATCH", "Booking not found", 403)
        if reservation.status == ReservationStatus.pending:
            reservation.payment_method = PaymentMethod.cash
            reservation = await ReservationService(session).confirm(reservation.id, actor_id=chat.user_id)
        if reservation.status != ReservationStatus.confirmed:
            raise DomainError("BOOKING_CLOSED", "Order is closed")
        await self.queue_tickets(session, reservation, chat.chat_id)
        await self.save(session, chat, stage="complete", reservation_code=reservation.public_code)
        await self.screen(chat.chat_id, T("done", code=esc(reservation.public_code)),
            keyboard([button(T("btn_my"), "mine")], [button(T("btn_another"), "book")]), message_id)

    async def queue_tickets(self, session, reservation, chat_id, resend=False):
        await queue_telegram_tickets(session, reservation.id, chat_id, resend=resend)
        await session.commit()

    async def my_tickets(self, session, chat, message_id=None):
        T = self.tr(chat)
        reservations = list((await session.scalars(select(Reservation).where(Reservation.telegram_chat_id == chat.chat_id).order_by(Reservation.created_at.desc()).limit(10))).all())
        rows = []
        for reservation in reservations:
            mark = "✅" if reservation.status == ReservationStatus.confirmed else "✖️" if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired} else "⏳"
            rows.append([button(f"{mark} {reservation.public_code} · {money(reservation.total_amount_minor, reservation.currency)}", f"view:{reservation.public_code}")])
        if reservations and self.has_app:
            rows.append([self.web_button(T("btn_my_app"), "/my")])
        rows.append([button(T("btn_find"), "book"), button(T("btn_home"), "home")])
        await self.screen(chat.chat_id, T("my_list") if reservations else T("my_empty"), keyboard(*rows), message_id)

    async def owned_booking(self, session, chat, code):
        reservation = await session.scalar(select(Reservation).where(Reservation.public_code == code, Reservation.telegram_chat_id == chat.chat_id))
        if not reservation:
            raise DomainError("RESERVATION_NOT_FOUND", "Booking not found")
        return await ReservationService(session).get_by_id(reservation.id)

    async def show_booking(self, session, chat, code, message_id=None):
        T = self.tr(chat)
        reservation = await self.owned_booking(session, chat, code)
        trip = await TripService(session).get(reservation.trip_id)
        status_key = f"status_{reservation.status.value}"
        status = T(status_key) if has_text(chat.lang or "uz", status_key) else T("status_pending")
        local = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        text = T("booking", code=esc(code), origin=esc(trip.route.origin_city.name), destination=esc(trip.route.destination_city.name),
                 when=f"{local:%d.%m.%Y, %H:%M}", seats=esc(", ".join(s.seat.seat_number for s in reservation.seats)), status=status,
                 price=money(reservation.total_amount_minor, reservation.currency),
                 payment=T("paid") if reservation.payment_status == PaymentStatus.paid else T("pay_on_board"))
        rows = []
        if reservation.status == ReservationStatus.confirmed:
            rows.append([button(T("btn_image"), f"image:{code}")])
            if trip.departure_datetime > utcnow() and reservation.payment_status == PaymentStatus.unpaid:
                rows.append([button(T("btn_cancel_trip"), f"cancelask:{code}")])
        rows.append([button(T("btn_all_tickets"), "mine"), button(T("btn_home"), "home")])
        await self.screen(chat.chat_id, text, keyboard(*rows), message_id)

    async def faq(self, session, chat, message_id=None):
        T = self.tr(chat)
        items = await list_faq(session, chat.lang or "uz")
        rows = [[button(item.question[:60], f"fq:{item.id}")] for item in items[:40]]
        rows.append([button(T("btn_support"), "support"), button(T("btn_home"), "home")])
        await self.screen(chat.chat_id, T("faq") if items else T("faq_empty"), keyboard(*rows), message_id)

    async def faq_item(self, session, chat, item_id, message_id=None):
        T = self.tr(chat)
        item = await session.get(FaqItem, UUID(item_id))
        if not item or not item.active:
            return await self.faq(session, chat, message_id)
        await self.screen(chat.chat_id, f"❓ <b>{esc(item.question)}</b>\n\n{esc(item.answer)}",
            keyboard([button(T("btn_faq_back"), "faq")], [button(T("btn_support"), "support"), button(T("btn_home"), "home")]), message_id)

    async def support(self, session, chat, message_id=None):
        T = self.tr(chat)
        settings = get_settings()
        contact = T("support_contact", contact=esc(settings.TELEGRAM_SUPPORT)) if settings.TELEGRAM_SUPPORT else ""
        online = bool(settings.TELEGRAM_SUPPORT_CHAT_ID)
        await self.save(session, chat, stage="support" if online else None)
        await self.screen(chat.chat_id, (T("support_intro") if online else T("support_offline")) + contact,
            keyboard([button(T("btn_faq"), "faq"), button(T("btn_home"), "home")]), message_id)

    async def support_forward(self, session, chat, sender, message):
        """Relay a passenger message into the support group, grouped into short threads."""
        T = self.tr(chat)
        group = get_settings().TELEGRAM_SUPPORT_CHAT_ID
        if not group:
            return await self.support(session, chat)
        recent = await session.scalar(select(TelegramSupportMessage).where(
            TelegramSupportMessage.chat_id == chat.chat_id,
            TelegramSupportMessage.created_at > utcnow() - SUPPORT_THREAD_WINDOW,
        ).order_by(TelegramSupportMessage.created_at.desc()).limit(1))
        links = []
        if recent:
            anchor = recent.group_message_id
        else:
            code = await session.scalar(select(Reservation.public_code).where(Reservation.telegram_chat_id == chat.chat_id).order_by(Reservation.created_at.desc()).limit(1))
            name = " ".join(filter(None, (sender.get("first_name"), sender.get("last_name")))) or "—"
            username = f" · @{sender['username']}" if sender.get("username") else ""
            card = await self._call("sendMessage", chat_id=group, parse_mode="HTML", text=(
                f"📨 <b>{esc(name)}</b>{esc(username)}\n🆔 <code>{chat.chat_id}</code> · {esc((chat.lang or 'uz').upper())}\n"
                f"📱 {esc(chat.phone or '—')}\n🧾 {esc(code or '—')}\n\n"
                "↩️ Ответьте на сообщение пассажира — ответ уйдёт ему в бот."))
            anchor = card["message_id"]
            links.append(anchor)
        copied = await self._call("copyMessage", chat_id=group, from_chat_id=chat.chat_id, message_id=message["message_id"],
                                  reply_parameters={"message_id": anchor, "allow_sending_without_reply": True})
        links.append(copied["message_id"])
        for group_message_id in links:
            await session.execute(insert(TelegramSupportMessage).values(group_message_id=group_message_id, chat_id=chat.chat_id)
                                  .on_conflict_do_nothing(index_elements=[TelegramSupportMessage.group_message_id]))
        await session.commit()
        await self.screen(chat.chat_id, T("support_sent"), keyboard([button(T("btn_support_done"), "supportdone")]))

    async def support_reply(self, session, message):
        """An operator replied in the support group: deliver it to the passenger."""
        reply = message.get("reply_to_message") or {}
        if not reply or message.get("from", {}).get("is_bot"):
            return
        link = await session.get(TelegramSupportMessage, reply.get("message_id"))
        if not link:
            return
        group = message["chat"]["id"]
        chat = await session.get(TelegramChat, link.chat_id)
        T = partial(t, chat.lang if chat and chat.lang else "uz")
        markup = keyboard([button(T("btn_support_answer"), "support")], [button(T("btn_home"), "home")])
        try:
            if message.get("text"):
                await self._call("sendMessage", chat_id=link.chat_id, parse_mode="HTML",
                                 text=T("support_reply") + "\n\n" + esc(message["text"]), reply_markup=markup)
            else:
                await self._call("sendMessage", chat_id=link.chat_id, parse_mode="HTML", text=T("support_reply"))
                await self._call("copyMessage", chat_id=link.chat_id, from_chat_id=group, message_id=message["message_id"], reply_markup=markup)
        except TelegramAPIError as error:
            if error.code != 403:
                raise
            return await self._call("sendMessage", chat_id=group, text="⚠️ Пассажир заблокировал бота — ответ не доставлен.",
                                    reply_parameters={"message_id": message["message_id"], "allow_sending_without_reply": True})
        # Replies to an operator's answer continue the same thread.
        await session.execute(insert(TelegramSupportMessage).values(group_message_id=message["message_id"], chat_id=link.chat_id)
                              .on_conflict_do_nothing(index_elements=[TelegramSupportMessage.group_message_id]))
        await session.commit()
        try:
            await self._call("setMessageReaction", chat_id=group, message_id=message["message_id"], reaction=[{"type": "emoji", "emoji": "👍"}])
        except TelegramAPIError:
            pass

    async def inline_query(self, session, query):
        """`@bot tosh sam` lists matching routes with a button that opens the Mini App on them."""
        T = partial(t, detect_lang(query.get("from", {}).get("language_code")))
        words = (query.get("query") or "").lower().split()[:4]
        results = []
        if getattr(self, "username", ""):
            origin, destination = aliased(City), aliased(City)
            rows = (await session.execute(
                select(Route.origin_city_id, Route.destination_city_id, Route.id, origin.name, destination.name,
                       func.min(Trip.base_price_minor), func.min(Trip.currency))
                .join(origin, origin.id == Route.origin_city_id)
                .join(destination, destination.id == Route.destination_city_id)
                .join(Trip, (Trip.route_id == Route.id) & (Trip.departure_datetime > utcnow()) & Trip.status.in_(BOOKABLE_TRIP_STATUSES))
                .where(Route.active.is_(True), origin.active.is_(True), destination.active.is_(True))
                .group_by(Route.id, origin.name, destination.name)
                .order_by(origin.name, destination.name))).all()
            for origin_id, destination_id, route_id, origin_name, destination_name, price, currency in rows:
                haystack = f"{origin_name} {destination_name}".lower()
                if not all(word in haystack for word in words):
                    continue
                results.append({
                    "type": "article", "id": route_id.hex,
                    "title": f"{origin_name} → {destination_name}",
                    "description": T("inline_desc", price=money(price, currency)),
                    "input_message_content": {"message_text": T("inline_message", origin=esc(origin_name), destination=esc(destination_name)), "parse_mode": "HTML"},
                    "reply_markup": keyboard([{"text": T("btn_inline_buy"), "url": self.app_link(route_param(origin_id, destination_id))}]),
                })
                if len(results) >= 20:
                    break
        await self._call("answerInlineQuery", inline_query_id=query["id"], results=results, cache_time=60,
                         button={"text": T("inline_open_bot"), "start_parameter": "inline"})

    async def handle_update(self, update, session):
        if update.get("inline_query"):
            return await self.inline_query(session, update["inline_query"])
        callback = update.get("callback_query")
        message = callback.get("message", {}) if callback else update.get("message", {})
        sender = callback.get("from", {}) if callback else message.get("from", {})
        chat_info = message.get("chat", {})
        support_group = get_settings().TELEGRAM_SUPPORT_CHAT_ID
        if support_group and not callback and chat_info.get("id") == support_group:
            return await self.support_reply(session, message)
        if chat_info.get("type") != "private" or chat_info.get("id") != sender.get("id") or sender.get("is_bot"):
            return
        chat_id = int(chat_info["id"])
        chat = await session.get(TelegramChat, chat_id)
        if not chat:
            chat = TelegramChat(chat_id=chat_id, data={}, lang=detect_lang(sender.get("language_code")))
            session.add(chat)
            await session.commit()
        elif not chat.lang:
            chat.lang = detect_lang(sender.get("language_code"))
            await session.commit()
        # Captured as plain values: a rollback below expires the ORM object.
        lang = chat.lang
        T = partial(t, lang)
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
                argument = text.partition(" ")[2].strip()
                if argument.startswith("check_"):
                    from app.services.telegram_admin import check
                    return await check(self, session, chat, argument[6:])
                if argument == "support":
                    return await self.support(session, chat)
                if argument == "faq":
                    return await self.faq(session, chat)
                if argument == "tickets":
                    return await self.my_tickets(session, chat)
                await self._call("sendMessage", chat_id=chat_id, text=T("welcome"), reply_markup={"remove_keyboard": True})
                return await self.home(session, chat)
            if command == "/book":
                return await self.open_app(session, chat)
            if command in {"/tickets", "/lookup"}:
                return await self.my_tickets(session, chat)
            if command in {"/faq", "/help"}:
                return await self.faq(session, chat)
            if command == "/support":
                return await self.support(session, chat)
            if command == "/lang":
                return await self.switch_lang(session, chat)
            if command == "/admin":
                from app.services.telegram_admin import menu
                return await menu(self, session, chat)
            if command == "/check":
                from app.services.telegram_admin import check
                return await check(self, session, chat, text.partition(" ")[2].strip())
            if message.get("contact"):
                contact = message["contact"]
                if contact.get("user_id") != sender.get("id"):
                    raise DomainError("CONTACT_NOT_YOURS", "Share your own contact")
                raw_phone = contact["phone_number"]
                phone = normalize_phone(raw_phone if raw_phone.startswith("+") else "+" + raw_phone)
                user = await ReservationService(session)._get_or_create_user(phone, None)
                chat.phone, chat.user_id = phone, user.id
                await session.commit()
                stage = chat.data.get("stage")
                if stage == "staff_phone":
                    await self._call("sendMessage", chat_id=chat_id, text=T("phone_saved"), reply_markup={"remove_keyboard": True})
                    from app.services.telegram_admin import menu
                    return await menu(self, session, chat)
                if stage == "phone":
                    await self._call("sendMessage", chat_id=chat_id, text=T("phone_saved"), reply_markup={"remove_keyboard": True})
                    return await self.passenger(session, chat, sender)
                # Shared from the Mini App checkout (requestContact): keep it, stay quiet.
                return
            if chat.data.get("stage") == "support":
                return await self.support_forward(session, chat, sender, message)
            if chat.data.get("stage") == "name" and text:
                return await self.review(session, chat, text)
            await self.screen(chat_id, T("use_buttons"), keyboard([button(T("btn_home"), "home"), button(T("btn_my"), "mine")]))
        except (ValueError, KeyError, TypeError):
            await session.rollback()
            await self.screen(chat_id, T("stale"), keyboard([button(T("btn_find"), "book"), button(T("btn_my"), "mine")]))
        except DomainError as error:
            await session.rollback()
            key = f"err_{error.code}"
            # Staff screens raise Russian messages meant to be shown as-is.
            text = T(key) if has_text(lang, key) else error.message if has_cyrillic(error.message) else T("error_generic")
            await self.screen(chat_id, esc(text), keyboard([button(T("btn_find"), "book"), button(T("btn_my"), "mine")]))

    async def handle_action(self, session, chat, sender, action, message_id):
        T = self.tr(chat)
        name, _, value = action.partition(":")
        if name.startswith("staff"):
            from app.services import telegram_admin
            if name == "staff":
                return await telegram_admin.menu(self, session, chat, message_id)
            if name in {"staffview", "staffpayask", "staffpaid"}:
                return await telegram_admin.booking(self, session, chat, value, message_id, action=name.removeprefix("staff"))
            if name in {"staffticket", "staffboard"}:
                return await telegram_admin.check(self, session, chat, value, message_id, board=name == "staffboard")
        if name in {"home", "supportdone"}:
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
                raise DomainError("STALE_BUTTON", "Confirm passenger again")
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
                raise DomainError("TICKET_INACTIVE", "Ticket is no longer valid")
            await self.queue_tickets(session, reservation, chat.chat_id, resend=True)
            return await self.screen(chat.chat_id, T("image_sending"), keyboard([button(T("btn_to_booking"), f"view:{value}")]), message_id)
        if name in {"cancelask", "cancel"}:
            reservation = await self.owned_booking(session, chat, value)
            trip = await session.get(Trip, reservation.trip_id)
            if reservation.payment_status != PaymentStatus.unpaid or trip.departure_datetime <= utcnow():
                raise DomainError("CANCEL_UNAVAILABLE", "Contact support to cancel")
            if name == "cancelask":
                return await self.screen(chat.chat_id, T("cancel_ask", code=esc(value)),
                    keyboard([button(T("btn_cancel_yes"), f"cancel:{value}")], [button(T("btn_keep"), f"view:{value}")]), message_id)
            if reservation.status not in {ReservationStatus.cancelled, ReservationStatus.expired}:
                await ReservationService(session).cancel(reservation.id, chat.user_id)
            return await self.show_booking(session, chat, value, message_id)
        if name in {"faq", "help"}:
            return await self.faq(session, chat, message_id)
        if name == "fq":
            return await self.faq_item(session, chat, value, message_id)
        if name == "support":
            return await self.support(session, chat, message_id)
        if name == "lang":
            return await self.switch_lang(session, chat, message_id)
        if name in {"noop", "unavailable"}:
            return
        return await self.home(session, chat, message_id)

    async def send_ticket(self, session, delivery):
        row = await session.get(Ticket, delivery.ticket_id)
        ticket = await TicketService(session).get_by_public_id(row.public_id)
        if ticket.status != TicketStatus.valid or ticket.reservation.status != ReservationStatus.confirmed:
            return
        if ticket.reservation.telegram_chat_id != delivery.chat_id:
            raise DomainError("BOOKING_OWNER_MISMATCH", "Ticket delivery owner mismatch", 403)
        chat = await session.get(TelegramChat, delivery.chat_id)
        T = partial(t, chat.lang if chat and chat.lang else "uz")
        trip = ticket.trip
        departure = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        arrival = trip.estimated_arrival_datetime.astimezone(ZoneInfo(trip.route.destination_city.timezone))
        qr_value = f"https://t.me/{self.username}?start=check_{ticket.qr_token}" if getattr(self, "username", "") else ticket.qr_token
        paid = ticket.reservation.payment_status == PaymentStatus.paid
        data = TicketImageData(
            public_id=ticket.public_id, booking_code=ticket.reservation.public_code, qr_token=qr_value,
            origin=trip.route.origin_city.name, destination=trip.route.destination_city.name,
            departure_date=departure.strftime("%d.%m.%Y"), departure_time=departure.strftime("%H:%M"), arrival_time=arrival.strftime("%d.%m %H:%M"),
            passenger=" ".join(filter(None, [ticket.passenger.first_name, ticket.passenger.last_name])), seat=ticket.seat.seat_number,
            bus=f"{trip.bus.name} · {trip.bus.registration_number}", boarding=trip.boarding_location or "Chiqish joyini tashuvchidan aniqlang",
            price=money(ticket.reservation.total_amount_minor, ticket.reservation.currency),
            payment="To‘langan" if paid else "To‘lov chiqishda", demo=get_settings().TELEGRAM_DEMO_MODE)
        png = await asyncio.to_thread(render_ticket, data)
        caption = T("ticket_caption", ticket=esc(ticket.public_id), origin=esc(data.origin), destination=esc(data.destination),
                    date=data.departure_date, time=data.departure_time, seat=esc(data.seat), payment=T("paid") if paid else T("pay_on_board"))
        if data.demo:
            caption += T("demo_ticket")
        rows = [[self.web_button(T("btn_open_ticket"), f"/ticket/{ticket.public_id}")]] if self.has_app else []
        rows += [[button(T("btn_open_booking"), f"view:{data.booking_code}")], [button(T("btn_my"), "mine")]]
        await self._call("sendPhoto", chat_id=delivery.chat_id, _photo=png, caption=caption, parse_mode="HTML", reply_markup=keyboard(*rows))

    async def send_reminders(self, session):
        """Remind Telegram passengers a day and two hours before departure, at most once each."""
        now = utcnow()
        soon = timedelta(hours=2)
        rows = (await session.execute(
            select(Reservation, Trip).join(Trip, Trip.id == Reservation.trip_id).where(
                Reservation.status == ReservationStatus.confirmed,
                Reservation.telegram_chat_id.is_not(None),
                Reservation.reminder_soon_sent_at.is_(None),
                Trip.departure_datetime > now,
                Trip.departure_datetime <= now + timedelta(hours=24),
                or_(Trip.departure_datetime <= now + soon, Reservation.reminder_day_sent_at.is_(None)),
            ).limit(50))).all()
        due = []
        for reservation, trip in rows:
            if trip.departure_datetime - now <= soon:
                reservation.reminder_soon_sent_at = now
                reservation.reminder_day_sent_at = reservation.reminder_day_sent_at or now
                # A booking made minutes ago needs no "departing soon" nudge.
                if now - reservation.created_at >= timedelta(hours=1):
                    due.append((reservation.id, "soon"))
            else:
                reservation.reminder_day_sent_at = now
                if trip.departure_datetime - reservation.created_at >= timedelta(hours=12):
                    due.append((reservation.id, "day"))
        # Marked before sending: a crash may lose a reminder but never repeats one.
        await session.commit()
        for reservation_id, kind in due:
            try:
                await self.send_reminder(session, reservation_id, kind)
            except Exception as error:
                logger.warning("telegram_reminder_failed reservation_id=%s error=%s", reservation_id, type(error).__name__)
        return len(due)

    async def send_reminder(self, session, reservation_id, kind):
        reservation = await session.get(Reservation, reservation_id)
        trip = await TripService(session).get(reservation.trip_id)
        chat = await session.get(TelegramChat, reservation.telegram_chat_id)
        T = partial(t, chat.lang if chat and chat.lang else "uz")
        local = trip.departure_datetime.astimezone(ZoneInfo(trip.route.origin_city.timezone))
        text = T(f"reminder_{kind}", origin=esc(trip.route.origin_city.name), destination=esc(trip.route.destination_city.name),
                 date=f"{local:%d.%m.%Y}", time=f"{local:%H:%M}", boarding=esc(trip.boarding_location or T("boarding_unknown")),
                 code=esc(reservation.public_code))
        await self._call("sendMessage", chat_id=reservation.telegram_chat_id, text=text, parse_mode="HTML",
                         reply_markup=keyboard([button(T("btn_open_booking"), f"view:{reservation.public_code}")]))


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
