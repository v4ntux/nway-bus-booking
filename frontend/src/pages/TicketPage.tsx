import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "@phosphor-icons/react";
import { bookingApi } from "../api/booking";
import { QrCode } from "../components/QrCode";
import { BrandWord } from "../components/BrandMark";
import { Badge, ErrorBox, Skeleton, backLinkClass, type Tone } from "../components/Ui";

const STATUS: Record<string, { label: string; tone: Tone }> = {
  valid: { label: "Haqiqiy", tone: "positive" },
  used: { label: "Foydalanilgan", tone: "neutral" },
  cancelled: { label: "Bekor qilingan", tone: "danger" },
};

export function TicketPage() {
  const { publicId = "" } = useParams();
  const query = useQuery({
    queryKey: ["ticket", publicId],
    queryFn: () => bookingApi.ticket(publicId),
  });

  const ticket = query.data;
  const status = ticket ? (STATUS[ticket.status] ?? { label: ticket.status, tone: "neutral" as Tone }) : null;

  return (
    <div className="flex flex-col gap-6">
      <Link to="/lookup" viewTransition className={backLinkClass}>
        <ArrowLeft size={15} weight="bold" />
        Boshqa chipta
      </Link>

      {query.isError && <ErrorBox error={query.error} />}
      {query.isLoading && <Skeleton className="mx-auto h-[420px] w-full max-w-sm" />}

      {ticket && status && (
        <article className="ticket-sheen mx-auto w-full max-w-sm animate-fade-rise overflow-hidden rounded-plate border border-line bg-surface shadow-lift">
          <div className="flex items-center justify-between gap-3 px-5 pb-4 pt-5">
            <BrandWord size="sm" />
            <Badge tone={status.tone}>{status.label}</Badge>
          </div>

          <div className="flex flex-col gap-4 px-5 pb-6">
            <div>
              <p className="text-[13px] text-muted">Yo‘lovchi</p>
              <p className="mt-0.5 text-[19px] font-semibold leading-tight text-ink">
                {[ticket.passenger?.first_name, ticket.passenger?.last_name].filter(Boolean).join(" ") || "-"}
              </p>
            </div>
            <div>
              <p className="text-[13px] text-muted">Joy</p>
              <p className="tnum mt-0.5 text-[34px] font-semibold leading-none text-ink">
                {ticket.seat_number ?? "-"}
              </p>
            </div>
          </div>

          {/* The tear line. Notches read as a real stub, not a card. */}
          <div className="relative flex items-center" aria-hidden="true">
            <span className="h-6 w-6 -translate-x-1/2 rounded-full bg-paper" />
            <span className="perforation h-px flex-1" />
            <span className="h-6 w-6 translate-x-1/2 rounded-full bg-paper" />
          </div>

          <div className="flex flex-col items-center gap-3 px-5 pb-7 pt-6">
            <QrCode value={ticket.qr_token} />
            <p className="tnum text-[15px] font-semibold tracking-[0.14em] text-ink">{ticket.public_id}</p>
            <p className="max-w-[30ch] text-center text-[13px] leading-relaxed text-muted">
              Chiqishda bu kodni haydovchiga ko‘rsating.
            </p>
          </div>
        </article>
      )}
    </div>
  );
}
