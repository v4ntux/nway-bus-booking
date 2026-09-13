"""Staff actions reuse existing user roles and company boundaries."""
from sqlalchemy import select
from zoneinfo import ZoneInfo

from app.core.exceptions import DomainError
from app.models import PaymentStatus, Reservation, ReservationStatus, Ticket, TicketStatus, User, UserRole, UserStatus
from app.services.payment import PaymentService
from app.services.reservation import ReservationService
from app.services.telegram_bot import button, esc, keyboard, money
from app.services.ticket import TicketService


async def staff(session, chat):
    user = await session.get(User, chat.user_id) if chat.user_id else None
    if not user or user.status != UserStatus.active or user.role not in {UserRole.superadmin, UserRole.admin, UserRole.operator, UserRole.driver}:
        raise DomainError("STAFF_REQUIRED", "Раздел доступен только сотрудникам перевозчика", 403)
    return user


def scope(actor, company_id):
    if actor.role != UserRole.superadmin and actor.company_id != company_id:
        raise DomainError("STAFF_SCOPE", "Этот заказ относится к другому перевозчику", 403)


async def menu(bot, session, chat, message_id=None):
    if not chat.phone:
        await bot.save(session, chat, stage="staff_phone")
        return await bot._call("sendMessage", chat_id=chat.chat_id, text="Для входа сотрудника поделитесь своим номером. Доступ проверяется по существующей учётной записи NWay.", reply_markup={"keyboard": [[{"text": "📱 Поделиться моим номером", "request_contact": True}]], "resize_keyboard": True, "one_time_keyboard": True})
    actor = await staff(session, chat)
    query = select(Reservation).where(Reservation.status == ReservationStatus.confirmed).order_by(Reservation.created_at.desc()).limit(15)
    if actor.role != UserRole.superadmin:
        query = query.where(Reservation.company_id == actor.company_id)
    bookings = list((await session.scalars(query)).all())
    rows = [[button(f"{'✅' if r.payment_status == PaymentStatus.paid else '💵'} {r.public_code} · {money(r.total_amount_minor, r.currency)}", f"staffview:{r.public_code}")] for r in bookings]
    rows.append([button("↻ Обновить", "staff"), button("⌂ Меню", "home")])
    await bot.screen(chat.chat_id, "<b>Пульт сотрудника</b>\n\nПоследние подтверждённые заказы. 💵 — оплата ещё не получена.\n\nДля посадки отсканируйте QR билета камерой телефона: откроется проверка в этом боте. Либо отправьте /check и код билета.", keyboard(*rows), message_id)


async def booking(bot, session, chat, code, message_id=None, action="view"):
    actor = await staff(session, chat)
    reservation = await ReservationService(session).get_by_public_code(code)
    scope(actor, reservation.company_id)
    if action == "payask":
        return await bot.screen(chat.chat_id, f"<b>Оплата действительно получена?</b>\n\nЗаказ {esc(code)}\nСумма: {money(reservation.total_amount_minor, reservation.currency)}\n\nПодтверждайте только после получения денег.", keyboard([button("Да, деньги получены", f"staffpaid:{code}")], [button("← Назад", f"staffview:{code}")]), message_id)
    if action == "paid":
        if actor.role == UserRole.driver:
            raise DomainError("STAFF_REQUIRED", "Оплату отмечает оператор или администратор", 403)
        await PaymentService(session).mark_paid_offline(reservation.id, actor.id)
        reservation = await ReservationService(session).get_by_id(reservation.id)
    tickets = await TicketService(session).list_for_reservation(reservation.id)
    rows = [[button(f"🎫 {t.public_id} · место {t.seat.seat_number}", f"staffticket:{t.public_id}")] for t in tickets]
    if reservation.payment_status != PaymentStatus.paid and actor.role != UserRole.driver:
        rows.append([button("💵 Отметить полученную оплату", f"staffpayask:{code}")])
    rows.append([button("← Заказы", "staff")])
    await bot.screen(chat.chat_id, f"<b>Заказ {esc(code)}</b>\n\nПассажир: {esc(', '.join(p.first_name for p in reservation.passengers))}\nТелефон: {esc(reservation.contact_phone)}\n{money(reservation.total_amount_minor, reservation.currency)}\nОплата: <b>{'получена' if reservation.payment_status == PaymentStatus.paid else 'при посадке'}</b>", keyboard(*rows), message_id)


async def check(bot, session, chat, value, message_id=None, board=False):
    actor = await staff(session, chat)
    row = await session.scalar(select(Ticket).where((Ticket.qr_token == value) | (Ticket.public_id == value.upper())))
    if not row:
        raise DomainError("TICKET_NOT_FOUND", "Билет не найден")
    ticket = await TicketService(session).get_by_public_id(row.public_id)
    scope(actor, ticket.reservation.company_id)
    if board:
        await TicketService(session).verify_qr(ticket.qr_token)
        ticket = await TicketService(session).get_by_public_id(row.public_id)
    status = {TicketStatus.valid: "✅ Действителен", TicketStatus.used: "☑️ Посадка уже отмечена", TicketStatus.cancelled: "⛔ Отменён"}[ticket.status]
    departure = ticket.trip.departure_datetime.astimezone(ZoneInfo(ticket.trip.route.origin_city.timezone))
    rows = []
    if ticket.status == TicketStatus.valid:
        rows.append([button("Подтвердить посадку пассажира", f"staffboard:{ticket.public_id}")])
    rows.append([button("← Заказ", f"staffview:{ticket.reservation.public_code}")])
    await bot.screen(chat.chat_id, f"<b>Проверка {esc(ticket.public_id)}</b>\n\n{status}\nПассажир: {esc(ticket.passenger.first_name)}\nМесто: {esc(ticket.seat.seat_number)}\n{esc(ticket.trip.route.origin_city.name)} → {esc(ticket.trip.route.destination_city.name)}\n📅 {departure:%d.%m.%Y, %H:%M}\n\n{'✅ Оплачено' if ticket.reservation.payment_status == PaymentStatus.paid else '💵 Оплата ещё не отмечена'}", keyboard(*rows), message_id)
