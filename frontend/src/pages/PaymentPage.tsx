import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { bookingApi } from "../api/booking";
import { Amount, Button, ErrorBox, Skeleton } from "../components/Ui";
import { useCountdown } from "../hooks/useCountdown";
import { useTelegram } from "../telegram/TelegramProvider";
import { clearDraft } from "../features/booking/draft";
import { formatCountdown, seatsWord } from "../utils/format";

export function PaymentPage() {
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const { isTelegram, haptic } = useTelegram();
  const query = useQuery({ queryKey: ["reservation", code], queryFn: () => bookingApi.getReservation(code) });
  const reservation = query.data;
  const { msLeft, expired } = useCountdown(reservation?.expires_at);
  const confirm = useMutation({
    mutationFn: () => bookingApi.confirmCash(code),
    onSuccess: (value) => {
      cache.setQueryData(["reservation", code], value);
      clearDraft();
      if (isTelegram) haptic("success");
      navigate(`/success/${code}`, { replace: true, viewTransition: true });
    },
  });

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-5">
      <div>
        <p className="mb-2 text-sm font-medium text-accent-strong">🎫 Oxirgi qadam</p>
        <h1 className="text-[28px] font-semibold tracking-tight text-ink">Bronni tasdiqlash</h1>
        <p className="mt-2 text-base text-muted">Joyingizni band qiling. To‘lovni safar kuni amalga oshirasiz.</p>
      </div>
      {query.isLoading && <Skeleton className="h-48 w-full" />}
      {query.isError && <ErrorBox error={query.error} />}
      {confirm.isError && <ErrorBox error={confirm.error} />}
      {reservation && <>
        {msLeft !== null && <p role="status" className="well rounded-panel px-4 py-3 text-sm text-muted">
          {expired ? "⌛ Bron muddati tugadi. Reysni qaytadan tanlang." : <>⏳ Joylar yana <strong className="tnum text-ink">{formatCountdown(msLeft)}</strong> ushlab turiladi</>}
        </p>}
        <div className="glass rounded-plate border-accent/40 p-5 shadow-glow">
          <div className="flex items-center gap-4">
            <span aria-hidden="true" className="well flex h-14 w-14 shrink-0 items-center justify-center rounded-panel text-3xl">💵</span>
            <div><h2 className="text-lg font-semibold text-ink">Avtobusga chiqishda to‘lash</h2>
              <p className="mt-1 text-sm leading-relaxed text-muted">Haydovchiga naqd pul bilan. Hozir pul yechilmaydi.</p></div>
          </div>
          <div className="mt-5 flex items-center justify-between gap-3 border-t border-hairline pt-4">
            <span className="text-sm text-muted">{seatsWord(reservation.seats.length)} · {reservation.public_code}</span>
            <Amount minor={reservation.total_amount_minor} currency={reservation.currency} className="text-xl font-semibold text-ink" />
          </div>
        </div>
        <div className="rounded-panel bg-accent-soft px-4 py-4 text-[15px] leading-relaxed text-accent-strong">
          {reservation.status === "awaiting_admin_approval"
            ? "👥 4 va undan ortiq joy uchun operator tasdig‘i kerak. Tasdiqlangach, chiptalar tayyor bo‘ladi."
            : isTelegram ? "💌 Tasdiqlangach, QR-chiptangiz rasm ko‘rinishida shu Telegram chatiga yuboriladi."
            : "🎫 Tasdiqlangach, QR-chiptani ochib saqlab oling va haydovchiga ko‘rsating."}
        </div>
        {expired ? <Link to="/book" className="no-underline"><Button block size="lg">Boshqa reys tanlash</Button></Link>
          : <Button block size="lg" loading={confirm.isPending} onClick={() => confirm.mutate()}>
            {confirm.isPending ? "Tasdiqlanmoqda…" : reservation.status === "awaiting_admin_approval" ? "📩 Operator tasdig‘ini kutish" : "✅ Bronni tasdiqlash"}
          </Button>}
        <p className="text-center text-xs leading-relaxed text-muted">Payme, Click va karta orqali to‘lov hali ulanmagan.</p>
      </>}
    </div>
  );
}
