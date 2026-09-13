import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toPng } from "html-to-image";
import {
  ArrowRight,
  Bus,
  Camera,
  Check,
  CheckCircle,
  Copy,
  DownloadSimple,
  Phone,
  Ticket as TicketIcon,
} from "@phosphor-icons/react";
import { bookingApi } from "../api/booking";
import { catalogApi } from "../api/catalog";
import { BrandWord } from "../components/BrandMark";
import { Amount, Badge, Button, ErrorBox, Skeleton, type Tone } from "../components/Ui";
import type { Reservation, Trip } from "../types/api";
import {
  PAYMENT_PROVIDER_UZ,
  formatClock,
  formatDateTimeLong,
  formatDayLabel,
  seatsWord,
} from "../utils/format";

const STATUS: Record<string, { label: string; tone: Tone; body: string }> = {
  confirmed: {
    label: "To‘lov qabul qilindi",
    tone: "positive",
    body: "Joylar siznikidir. Quyidagi chek sizning chiptangiz: uni saqlab qo‘ying va haydovchiga ko‘rsating.",
  },
  pending: {
    label: "To‘lov kutilmoqda",
    tone: "accent",
    body: "Joylar vaqtincha ushlab turilgan. To‘lovni yakunlang.",
  },
  awaiting_admin_approval: {
    label: "Tasdiqlanmoqda",
    tone: "accent",
    body: "Operator ko‘rsatilgan raqamga qo‘ng‘iroq qilib, bronni tasdiqlaydi.",
  },
  awaiting_deposit: {
    label: "Oldindan to‘lov kerak",
    tone: "accent",
    body: "Operator siz bilan bog‘lanib, summani aytadi.",
  },
  cancelled: { label: "Bekor qilingan", tone: "danger", body: "Joylar bo‘shatildi." },
  expired: { label: "Muddati tugagan", tone: "danger", body: "Bron vaqti tugadi, joylar bo‘shatildi." },
};

const PAYMENT_STATUS_UZ: Record<string, string> = {
  paid: "to‘langan",
  pending: "kutilmoqda",
  unpaid: "to‘lanmagan",
  failed: "muvaffaqiyatsiz",
  refunded: "qaytarilgan",
  partially_paid: "qisman to‘langan",
};

function CopyCode({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard?.writeText(code).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 2000);
        });
      }}
      className="glass inline-flex h-9 items-center gap-2 rounded-[11px] px-3 text-[13px] font-medium text-muted transition-colors duration-200 hover:text-ink"
    >
      {copied ? <Check size={15} weight="bold" className="text-positive" /> : <Copy size={15} weight="bold" />}
      {copied ? "Nusxalandi" : "Nusxalash"}
    </button>
  );
}

function Row({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="shrink-0 text-[13px] text-muted">{label}</dt>
      <dd className={`text-right text-[15px] font-medium text-ink ${mono ? "tnum" : ""}`}>{value}</dd>
    </div>
  );
}

/**
 * The receipt is the ticket. Solid surface on purpose: it has to survive a
 * screenshot and a PNG export, and frosted glass does not.
 */
function Receipt({ r, trip }: { r: Reservation; trip: Trip | undefined }) {
  const origin = trip?.route?.origin_city;
  const destination = trip?.route?.destination_city;
  const payment =
    r.payments.find((p) => p.status === "paid") ??
    [...r.payments].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  const seatByPassenger = new Map(r.seats.map((s) => [s.seat_id, s.seat_number]));

  return (
    <div className="flex flex-col gap-5 p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <BrandWord size="sm" />
        <span className="tnum text-[12px] text-muted">{formatDateTimeLong(r.created_at, origin?.timezone)}</span>
      </div>

      {trip ? (
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="tnum text-[34px] font-semibold leading-none text-ink">
              {formatClock(trip.departure_datetime, origin?.timezone)}
            </p>
            <p className="mt-2 truncate text-[16px] font-semibold text-ink">{origin?.name ?? "-"}</p>
            <p className="text-[13px] text-muted">{formatDayLabel(trip.departure_datetime, origin?.timezone)}</p>
            {trip.boarding_location && <p className="mt-1 text-[12.5px] text-faint">{trip.boarding_location}</p>}
          </div>
          <ArrowRight size={22} weight="bold" className="mt-2 shrink-0 text-accent" aria-hidden="true" />
          <div className="min-w-0 text-right">
            <p className="tnum text-[34px] font-semibold leading-none text-ink">
              {formatClock(trip.estimated_arrival_datetime, destination?.timezone)}
            </p>
            <p className="mt-2 truncate text-[16px] font-semibold text-ink">{destination?.name ?? "-"}</p>
            <p className="text-[13px] text-muted">
              {formatDayLabel(trip.estimated_arrival_datetime, destination?.timezone)}
            </p>
            {trip.destination_location && (
              <p className="mt-1 text-[12.5px] text-faint">{trip.destination_location}</p>
            )}
          </div>
        </div>
      ) : (
        <Skeleton className="h-20 w-full" />
      )}

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-y border-hairline py-3 text-[13.5px] text-muted">
        {trip?.bus && (
          <span className="inline-flex items-center gap-1.5">
            <Bus size={16} weight="regular" aria-hidden="true" />
            {trip.bus.model}
            <span className="tnum rounded-[6px] border border-line px-1.5 py-px text-[12px] font-semibold text-ink">
              {trip.bus.registration_number}
            </span>
          </span>
        )}
        <span className="inline-flex items-center gap-1.5">
          <Phone size={16} weight="regular" aria-hidden="true" />
          <span className="tnum text-ink">{r.contact_phone}</span>
        </span>
      </div>

      <div>
        <p className="mb-2 text-[13px] text-muted">{seatsWord(r.seats.length)}, yo‘lovchilar</p>
        <ul className="flex flex-col gap-1.5">
          {r.passengers.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 rounded-[12px] bg-raised px-3 py-2.5">
              <span className="truncate text-[15px] font-medium text-ink">
                {[p.first_name, p.last_name].filter(Boolean).join(" ")}
              </span>
              <span className="tnum shrink-0 rounded-[8px] bg-accent-soft px-2 py-0.5 text-[13px] font-semibold text-accent-strong">
                {seatByPassenger.get(p.seat_id) ?? "-"}-joy
              </span>
            </li>
          ))}
        </ul>
      </div>

      <dl className="flex flex-col gap-2.5">
        <Row
          label="To‘lov usuli"
          value={payment ? PAYMENT_PROVIDER_UZ[payment.provider] ?? payment.provider : "-"}
        />
        <Row
          label="To‘lov holati"
          value={
            <Badge tone={r.payment_status === "paid" ? "positive" : "accent"}>
              {PAYMENT_STATUS_UZ[r.payment_status] ?? r.payment_status}
            </Badge>
          }
        />
        {payment?.paid_at && (
          <Row label="To‘langan vaqt" value={formatDateTimeLong(payment.paid_at, origin?.timezone)} mono />
        )}
        <Row
          label="Summa"
          value={<Amount minor={r.total_amount_minor} currency={r.currency} className="text-[19px] font-semibold" />}
        />
      </dl>

      <div className="relative -mx-5 flex items-center sm:-mx-6" aria-hidden="true">
        <span className="h-6 w-6 -translate-x-1/2 rounded-full bg-paper" />
        <span className="perforation h-px flex-1" />
        <span className="h-6 w-6 translate-x-1/2 rounded-full bg-paper" />
      </div>

      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-[13px] text-muted">Bron kodi</p>
        <p className="tnum text-[32px] font-semibold leading-none tracking-[0.12em] text-ink">{r.public_code}</p>
        <p className="mt-1 max-w-[34ch] text-[12.5px] leading-relaxed text-faint">
          Chiqishda haydovchiga shu kodni yoki quyidagi QR-chiptani ko‘rsating.
        </p>
      </div>
    </div>
  );
}

export function SuccessPage() {
  const { code = "" } = useParams();
  const sheet = useRef<HTMLDivElement>(null);
  const [saving, setSaving] = useState(false);

  const query = useQuery({
    queryKey: ["reservation", code],
    queryFn: () => bookingApi.getReservation(code),
  });
  const r = query.data;
  const tripQuery = useQuery({
    queryKey: ["trip", r?.trip_id],
    queryFn: () => catalogApi.trip(r!.trip_id),
    enabled: Boolean(r?.trip_id),
  });
  const tickets = useQuery({
    queryKey: ["tickets", code],
    queryFn: () => bookingApi.tickets(code),
    enabled: r?.status === "confirmed",
  });

  const status = r ? (STATUS[r.status] ?? { label: r.status, tone: "neutral" as Tone, body: "" }) : null;

  async function download() {
    if (!sheet.current) return;
    setSaving(true);
    try {
      const paper = getComputedStyle(document.documentElement).getPropertyValue("--c-surface").trim();
      const url = await toPng(sheet.current, {
        pixelRatio: 2,
        cacheBust: true,
        backgroundColor: `rgb(${paper})`,
      });
      const a = document.createElement("a");
      a.href = url;
      a.download = `nway-${code}.png`;
      a.click();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {query.isLoading && <Skeleton className="h-64 w-full" />}
      {query.isError && <ErrorBox error={query.error} />}

      {r && status && (
        <>
          <header className="flex animate-fade-rise flex-col items-start gap-3">
            {r.status === "confirmed" && (
              <span className="success-ring inline-flex rounded-full">
                <CheckCircle
                  size={44}
                  weight="fill"
                  className="animate-pop-in text-positive drop-shadow-[0_0_18px_rgb(var(--c-positive)/0.55)]"
                />
              </span>
            )}
            <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.02em] text-ink sm:text-[34px]">
              {status.label}
            </h1>
            <p className="max-w-[50ch] text-[16px] leading-relaxed text-muted">{status.body}</p>
          </header>

          {r.status === "confirmed" && (
            <div className="flex items-start gap-3 rounded-panel border border-accent/40 bg-accent-soft/90 px-4 py-3.5 backdrop-blur-md">
              <Camera size={22} weight="duotone" className="mt-0.5 shrink-0 text-accent-strong" aria-hidden="true" />
              <p className="text-[14.5px] leading-relaxed text-accent-strong">
                <span className="font-semibold">Skrinshot qiling.</span> Bu chek sizning chiptangiz. Internet
                bo‘lmasa ham, haydovchiga rasmni ko‘rsatish kifoya.
              </p>
            </div>
          )}

          <article
            ref={sheet}
            className="ticket-sheen mx-auto w-full max-w-md overflow-hidden rounded-plate border border-line bg-surface shadow-lift"
          >
            <Receipt r={r} trip={tripQuery.data} />
          </article>

          <div className="mx-auto flex w-full max-w-md flex-col gap-3 sm:flex-row">
            <Button
              size="lg"
              block
              loading={saving}
              onClick={download}
              icon={saving ? undefined : <DownloadSimple size={18} weight="bold" />}
            >
              Chiptani yuklab olish
            </Button>
            <CopyCode code={r.public_code} />
          </div>

          {tickets.data && tickets.data.length > 0 && (
            <div className="mx-auto flex w-full max-w-md flex-col gap-3">
              <h2 className="text-[17px] font-semibold text-ink">
                {tickets.data.length > 1 ? "QR-chiptalar" : "QR-chipta"}
              </h2>
              <ul className="flex flex-col gap-2">
                {tickets.data.map((t) => (
                  <li key={t.id}>
                    <Link
                      to={`/ticket/${t.public_id}`}
                      viewTransition
                      className="glass glass-lift flex items-center justify-between gap-3 rounded-panel px-4 py-3.5 no-underline"
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <TicketIcon size={20} weight="regular" className="shrink-0 text-accent" />
                        <span className="min-w-0">
                          <span className="block truncate text-[15px] font-medium text-ink">
                            {[t.passenger?.first_name, t.passenger?.last_name].filter(Boolean).join(" ") ||
                              "Yo‘lovchi"}
                          </span>
                          <span className="tnum block text-[13px] text-muted">{t.seat_number}-joy</span>
                        </span>
                      </span>
                      <span className="text-[14px] font-medium text-ink">Ochish</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Link to="/" viewTransition className="mx-auto w-full max-w-md no-underline">
            <Button variant="secondary" size="lg" block>
              Yana chipta olish
            </Button>
          </Link>
        </>
      )}
    </div>
  );
}
