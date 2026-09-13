from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DomainError, NotFoundError
from app.core.config import get_settings
from app.models import Payment, PaymentMethod, PaymentStatus, Reservation, ReservationStatus
from app.services.audit import write_audit
from app.services.reservation import ReservationService
from app.utils.time import utcnow


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    async def create_payment(self, amount_minor: int, currency: str, metadata: dict) -> dict:
        ...

    @abstractmethod
    async def verify_payment(self, provider_payment_id: str) -> dict:
        ...

    @abstractmethod
    async def refund(self, provider_payment_id: str, amount_minor: int) -> dict:
        ...


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    async def create_payment(self, amount_minor: int, currency: str, metadata: dict) -> dict:
        return {
            "provider_payment_id": f"mock_{uuid4().hex[:16]}",
            "status": "pending",
            "amount_minor": amount_minor,
            "currency": currency,
        }

    async def verify_payment(self, provider_payment_id: str) -> dict:
        return {"provider_payment_id": provider_payment_id, "status": "paid"}

    async def refund(self, provider_payment_id: str, amount_minor: int) -> dict:
        return {"provider_payment_id": provider_payment_id, "status": "refunded", "amount_minor": amount_minor}


class PaymeProvider(MockPaymentProvider):
    """Payme (Paycom) checkout. Sandbox behaviour until merchant keys arrive."""

    name = "payme"


class ClickProvider(MockPaymentProvider):
    """Click Evolution. Sandbox behaviour until merchant keys arrive."""

    name = "click"


class CardProvider(MockPaymentProvider):
    """Uzcard / Humo card form via acquiring bank."""

    name = "card"


payment_providers: dict[str, PaymentProvider] = {
    "mock": MockPaymentProvider(),
    "payme": PaymeProvider(),
    "click": ClickProvider(),
    "card": CardProvider(),
}


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reservations = ReservationService(session)

    def _provider(self, name: str) -> PaymentProvider:
        if not get_settings().ALLOW_MOCK_PAYMENTS:
            raise DomainError("ONLINE_PAYMENT_UNAVAILABLE", "Online payment is not connected. Pay at boarding.", 409)
        provider = payment_providers.get(name)
        if provider is None:
            raise DomainError("UNKNOWN_PROVIDER", f"Unknown payment provider: {name}")
        return provider

    async def create_for_reservation(
        self,
        reservation_id: UUID,
        method: PaymentMethod,
        provider_name: str = "mock",
        actor_id: UUID | None = None,
    ) -> Payment:
        reservation = await self.session.get(Reservation, reservation_id)
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        if reservation.status in {
            ReservationStatus.cancelled,
            ReservationStatus.expired,
            ReservationStatus.no_show,
        }:
            raise DomainError("PAYMENT_NOT_ALLOWED", "Cannot pay a cancelled or expired booking", status_code=409)

        if method in {PaymentMethod.cash, PaymentMethod.transfer, PaymentMethod.other}:
            await self.reservations.choose_pay_later(reservation_id, method)
            payment = Payment(
                reservation_id=reservation_id,
                provider="offline",
                method=method,
                amount_minor=reservation.total_amount_minor,
                currency=reservation.currency,
                status=PaymentStatus.pending,
                extra_data={"mode": "pay_later"},
                created_at=utcnow(),
            )
            self.session.add(payment)
            reservation.payment_method = method
            await self.session.commit()
            return await self.get(payment.id)

        provider = self._provider(provider_name)
        created = await provider.create_payment(
            reservation.total_amount_minor,
            reservation.currency,
            {"reservation_id": str(reservation_id)},
        )
        payment = Payment(
            reservation_id=reservation_id,
            provider=provider.name,
            method=method,
            amount_minor=reservation.total_amount_minor,
            currency=reservation.currency,
            status=PaymentStatus.pending,
            provider_payment_id=created["provider_payment_id"],
            extra_data=created,
            created_at=utcnow(),
        )
        self.session.add(payment)
        reservation.payment_status = PaymentStatus.pending
        reservation.payment_method = method
        await self.session.flush()
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="payment.create",
            entity_type="payment",
            entity_id=payment.id,
            after={"method": method.value, "provider": provider.name},
        )
        await self.session.commit()
        return await self.get(payment.id)

    async def mock_success(self, payment_id: UUID) -> Payment:
        if not get_settings().ALLOW_MOCK_PAYMENTS:
            raise DomainError("MOCK_PAYMENTS_DISABLED", "Test payments are disabled", 403)
        payment = await self.get(payment_id)
        if payment.status == PaymentStatus.paid:
            return payment
        reservation = await self.session.get(Reservation, payment.reservation_id)
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired}:
            raise DomainError("PAYMENT_NOT_ALLOWED", "Cannot pay a cancelled booking", status_code=409)
        provider = self._provider(payment.provider if payment.provider != "offline" else "mock")
        if payment.provider_payment_id:
            await provider.verify_payment(payment.provider_payment_id)
        payment.status = PaymentStatus.paid
        payment.paid_at = utcnow()
        reservation.payment_status = PaymentStatus.paid
        await self.session.flush()
        if reservation.status == ReservationStatus.pending:
            await self.reservations.confirm(reservation.id, actor_id=None)
        else:
            await self.session.commit()
        return await self.get(payment.id)

    async def mock_fail(self, payment_id: UUID) -> Payment:
        if not get_settings().ALLOW_MOCK_PAYMENTS:
            raise DomainError("MOCK_PAYMENTS_DISABLED", "Test payments are disabled", 403)
        payment = await self.get(payment_id)
        reservation = await self.session.get(Reservation, payment.reservation_id)
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        if reservation.status in {ReservationStatus.cancelled, ReservationStatus.expired}:
            raise DomainError("PAYMENT_NOT_ALLOWED", "Cannot pay a cancelled booking", status_code=409)
        payment.status = PaymentStatus.failed
        reservation.payment_status = PaymentStatus.failed
        await self.session.commit()
        return await self.get(payment.id)

    async def mark_paid_offline(self, reservation_id: UUID, actor_id: UUID | None) -> Payment:
        reservation = await self.session.scalar(select(Reservation).where(Reservation.id == reservation_id).with_for_update().execution_options(populate_existing=True))
        if reservation is None:
            raise NotFoundError("RESERVATION_NOT_FOUND", "Booking not found")
        if reservation.status not in {ReservationStatus.pending, ReservationStatus.confirmed, ReservationStatus.awaiting_admin_approval}:
            raise DomainError("PAYMENT_NOT_ALLOWED", "Booking cannot be paid in this status", 409)
        if reservation.payment_status == PaymentStatus.paid:
            existing = await self.session.scalar(select(Payment).where(Payment.reservation_id == reservation_id, Payment.status == PaymentStatus.paid))
            if existing:
                return existing
        payment = Payment(
            reservation_id=reservation_id,
            provider="offline",
            method=reservation.payment_method or PaymentMethod.cash,
            amount_minor=reservation.total_amount_minor,
            currency=reservation.currency,
            status=PaymentStatus.paid,
            extra_data={"marked_by_admin": True},
            created_at=utcnow(),
            paid_at=utcnow(),
        )
        self.session.add(payment)
        await self.session.flush()
        reservation.payment_status = PaymentStatus.paid
        await write_audit(
            self.session,
            actor_id=actor_id,
            action="payment.mark_paid",
            entity_type="payment",
            entity_id=payment.id,
        )
        await self.session.flush()
        if reservation.status == ReservationStatus.confirmed:
            await self.session.commit()
        else:
            await self.reservations.confirm(reservation_id, actor_id=actor_id)
        return await self.get(payment.id)

    async def get(self, payment_id: UUID) -> Payment:
        result = await self.session.execute(
            select(Payment).options(selectinload(Payment.reservation)).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise NotFoundError("PAYMENT_NOT_FOUND", "Payment not found")
        return payment
