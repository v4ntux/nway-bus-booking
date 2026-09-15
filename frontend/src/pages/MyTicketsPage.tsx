import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, PaperPlaneTilt, Receipt, Ticket as TicketIcon, XCircle } from "@phosphor-icons/react";
import { bookingApi } from "../api/booking";
import { Dialog } from "../components/Dialog";
import { Amount, Badge, Button, EmptyState, ErrorBox, PageTitle, Skeleton, type Tone } from "../components/Ui";
import { useTelegram } from "../telegram/TelegramProvider";
import type { MyReservation } from "../types/api";
import { formatClock, formatDayLabel, seatsWord } from "../utils/format";

const STATUS: Record<string, { label: string; tone: Tone }> = {
  confirmed: { label: "Tasdiqlangan", tone: "positive" },
  pending: { label: "Tasdiq kutilmoqda", tone: "accent" },
  awaiting_admin_approval: { label: "Operator tasdiqlaydi", tone: "accent" },
  awaiting_deposit: { label: "Oldindan to‘lov kerak", tone: "accent" },
  cancelled: { label: "Bekor qilingan", tone: "danger" },
  expired: { label: "Muddati tugagan", tone: "danger" },
  completed: { label: "Safar yakunlangan", tone: "neutral" },
  no_show: { label: "Kelmadi", tone: "neutral" },
};

function BookingCard({ r, onCancel }: { r: MyReservation; onCancel: (r: MyReservation) => void }) {
  const { haptic } = useTelegram();
  const status = STATUS[r.status] ?? { label: r.status, tone: "neutral" as Tone };
  const upcoming = new Date(r.trip.departure_datetime).getTime() > Date.now();
  const resend = useMutation({
    mutationFn: () => bookingApi.resendToTelegram(r.public_code),
    onSuccess: () => haptic("success"),
  });

  return (
    <li className={`glass flex flex-col gap-4 rounded-plate p-4 sm:p-5 ${upcoming ? "" : "opacity-75"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-[17px] font-semibold text-ink">
            {r.trip.origin_city} → {r.trip.destination_city}
          </p>
          <p className="tnum mt-1 text-[14px] text-muted">
            {formatDayLabel(r.trip.departure_datetime, r.trip.origin_timezone)} ·{" "}
            {formatClock(r.trip.departure_datetime, r.trip.origin_timezone)}
          </p>
          {r.trip.boarding_location && <p className="mt-0.5 truncate text-[13px] text-faint">{r.trip.boarding_location}</p>}
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-y border-hairline py-3 text-[14px]">
        <span className="text-muted">
          {seatsWord(r.seats.length)}: <span className="tnum text-ink">{r.seats.map((s) => s.seat_number).join(", ")}</span>
        </span>
        <span className="flex items-center gap-2">
          <Amount minor={r.total_amount_minor} currency={r.currency} className="font-semibold text-ink" />
          <span className="text-[12.5px] text-muted">{r.payment_status === "paid" ? "to‘langan" : "chiqishda to‘lanadi"}</span>
        </span>
      </div>

      {r.status === "confirmed" && r.tickets.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {r.tickets.map((t) => (
            <li key={t.public_id}>
              <Link
                to={`/ticket/${t.public_id}`}
                viewTransition
                className="flex items-center justify-between gap-3 rounded-[12px] bg-raised px-3 py-2.5 no-underline"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <TicketIcon size={18} className="shrink-0 text-accent" aria-hidden="true" />
                  <span className="truncate text-[14.5px] font-medium text-ink">{t.passenger_name || "Yo‘lovchi"}</span>
                </span>
                <span className="tnum flex shrink-0 items-center gap-1.5 text-[13px] font-semibold text-accent-strong">
                  {t.seat_number}-joy <ArrowRight size={14} weight="bold" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {resend.isError && <ErrorBox error={resend.error} />}
      {resend.isSuccess && (
        <p role="status" className="text-[13.5px] text-positive">
          Chipta rasmi Telegram chatiga yuborildi.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Link to={`/success/${r.public_code}`} viewTransition className="no-underline">
          <Button variant="secondary" size="sm" icon={<Receipt size={15} weight="bold" />}>
            {r.public_code}
          </Button>
        </Link>
        {r.status === "confirmed" && upcoming && (
          <Button
            variant="secondary"
            size="sm"
            loading={resend.isPending}
            onClick={() => resend.mutate()}
            icon={resend.isPending ? undefined : <PaperPlaneTilt size={15} weight="bold" />}
          >
            Chatga yuborish
          </Button>
        )}
        {r.can_cancel && (
          <Button variant="ghost" size="sm" onClick={() => onCancel(r)} icon={<XCircle size={15} weight="bold" />}>
            Bekor qilish
          </Button>
        )}
      </div>
    </li>
  );
}

export function MyTicketsPage() {
  const { isTelegram, haptic } = useTelegram();
  const cache = useQueryClient();
  const [cancelling, setCancelling] = useState<MyReservation | null>(null);
  const query = useQuery({ queryKey: ["my-reservations"], queryFn: bookingApi.mine, enabled: isTelegram });
  const cancel = useMutation({
    mutationFn: (code: string) => bookingApi.cancel(code),
    onSuccess: () => {
      haptic("success");
      setCancelling(null);
      cache.invalidateQueries({ queryKey: ["my-reservations"] });
    },
  });

  if (!isTelegram) {
    return (
      <EmptyState
        icon={<TicketIcon size={36} />}
        title="Chiptalarim — Telegram ichida"
        body="Botdan ochilganda barcha bronlaringiz shu yerda ko‘rinadi. Brauzerda bronni telefon va kod bo‘yicha toping."
        action={
          <Link to="/lookup" viewTransition className="no-underline">
            <Button>Bronni topish</Button>
          </Link>
        }
      />
    );
  }

  const items = query.data ?? [];
  const now = Date.now();
  const upcoming = items.filter((r) => new Date(r.trip.departure_datetime).getTime() > now);
  const past = items.filter((r) => new Date(r.trip.departure_datetime).getTime() <= now);

  return (
    <div className="flex flex-col gap-6">
      <PageTitle sub="Bronlar, QR-chiptalar va bekor qilish">Chiptalarim</PageTitle>

      {query.isLoading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-44 w-full" />
          <Skeleton className="h-44 w-full" />
        </div>
      )}
      {query.isError && <ErrorBox error={query.error} />}

      {query.isSuccess && items.length === 0 && (
        <EmptyState
          icon={<TicketIcon size={36} />}
          title="Hozircha chipta yo‘q"
          body="Reys tanlang — tasdiqlangan chiptangiz shu yerda paydo bo‘ladi."
          action={
            <Link to="/book" viewTransition className="no-underline">
              <Button>Reys topish</Button>
            </Link>
          }
        />
      )}

      {upcoming.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-[15px] font-semibold text-muted">Oldinda</h2>
          <ul className="flex flex-col gap-3">
            {upcoming.map((r) => (
              <BookingCard key={r.id} r={r} onCancel={setCancelling} />
            ))}
          </ul>
        </section>
      )}

      {past.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-[15px] font-semibold text-muted">O‘tgan safarlar</h2>
          <ul className="flex flex-col gap-3">
            {past.map((r) => (
              <BookingCard key={r.id} r={r} onCancel={setCancelling} />
            ))}
          </ul>
        </section>
      )}

      <Dialog open={cancelling !== null} onClose={() => setCancelling(null)} title="Bronni bekor qilasizmi?">
        {cancelling && (
          <div className="flex flex-col gap-4">
            <p className="text-[15px] leading-relaxed text-muted">
              {cancelling.trip.origin_city} → {cancelling.trip.destination_city}, {cancelling.public_code}. Joy boshqa
              yo‘lovchilarga bo‘shaydi, QR-chipta amal qilmay qoladi.
            </p>
            {cancel.isError && <ErrorBox error={cancel.error} />}
            <Button variant="danger" size="lg" block loading={cancel.isPending} onClick={() => cancel.mutate(cancelling.public_code)}>
              Ha, bekor qilish
            </Button>
            <Button variant="secondary" size="lg" block onClick={() => setCancelling(null)}>
              Safarni saqlash
            </Button>
          </div>
        )}
      </Dialog>
    </div>
  );
}
