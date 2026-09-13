from app.models import Reservation, Ticket
from app.schemas.booking import (
    PaymentOut,
    ReservationOut,
    ReservationPassengerOut,
    ReservationSeatOut,
    TicketOut,
)


def reservation_to_out(reservation: Reservation) -> ReservationOut:
    seats = []
    for item in reservation.seats:
        seats.append(
            ReservationSeatOut(
                seat_id=item.seat_id,
                price_minor=item.price_minor,
                is_active_hold=item.is_active_hold,
                seat_number=item.seat.seat_number if item.seat else None,
            )
        )
    return ReservationOut(
        id=reservation.id,
        public_code=reservation.public_code,
        trip_id=reservation.trip_id,
        company_id=reservation.company_id,
        status=reservation.status,
        payment_status=reservation.payment_status,
        payment_method=reservation.payment_method,
        total_amount_minor=reservation.total_amount_minor,
        currency=reservation.currency,
        expires_at=reservation.expires_at,
        contact_phone=reservation.contact_phone,
        deposit_required=reservation.deposit_required,
        deposit_received=reservation.deposit_received,
        created_at=reservation.created_at,
        seats=seats,
        passengers=[ReservationPassengerOut.model_validate(p) for p in reservation.passengers],
        payments=[PaymentOut.model_validate(p) for p in reservation.payments],
    )


def ticket_to_out(ticket: Ticket) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        public_id=ticket.public_id,
        qr_token=ticket.qr_token,
        reservation_id=ticket.reservation_id,
        trip_id=ticket.trip_id,
        seat_id=ticket.seat_id,
        status=ticket.status,
        passenger=ReservationPassengerOut.model_validate(ticket.passenger) if ticket.passenger else None,
        seat_number=ticket.seat.seat_number if ticket.seat else None,
    )
