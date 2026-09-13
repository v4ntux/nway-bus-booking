import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, CreditCard, Money, Timer } from "@phosphor-icons/react";
import { bookingApi } from "../api/booking";
import { Amount, Button, ErrorBox, Skeleton } from "../components/Ui";
import { useCountdown } from "../hooks/useCountdown";
import { formatCountdown, seatsWord } from "../utils/format";

type Provider = "payme" | "click" | "card";

/*
 * Payme and Click are the two wallets every passenger in Uzbekistan already
 * has, so they get real brand marks. The card option covers Uzcard and Humo,
 * the two domestic card networks.
 */
const PROVIDERS: { id: Provider; title: string; body: string }[] = [
  { id: "payme", title: "Payme", body: "Payme ilovasi yoki karta orqali. Joy darhol tasdiqlanadi." },
  { id: "click", title: "Click", body: "Click ilovasi yoki USSD orqali. Joy darhol tasdiqlanadi." },
  { id: "card", title: "Uzcard / Humo", body: "Karta raqami va SMS-kod. Joy darhol tasdiqlanadi." },
];

function ProviderMark({ id }: { id: Provider }) {
  if (id === "payme") {
    return (
      <span
        aria-hidden="true"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[13px] bg-[#33CCCC] text-[15px] font-bold tracking-tight text-white shadow-[0_8px_20px_-8px_rgb(51_204_204/0.8)]"
      >
        pay
        <span className="text-[#0B2E45]">me</span>
      </span>
    );
  }
  if (id === "click") {
    return (
      <span
        aria-hidden="true"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[13px] bg-[#0073FF] shadow-[0_8px_20px_-8px_rgb(0_115_255/0.8)]"
      >
        <Check size={22} weight="bold" className="text-white" />
      </span>
    );
  }
  return (
    <span
      aria-hidden="true"
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[13px] bg-gradient-to-br from-[#1E3A8A] to-[#0F766E] text-white shadow-[0_8px_20px_-8px_rgb(30_58_138/0.8)]"
    >
      <CreditCard size={22} weight="fill" />
    </span>
  );
}

export function PaymentPage() {
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const [provider, setProvider] = useState<Provider>("payme");

  const query = useQuery({
    queryKey: ["reservation", code],
    queryFn: () => bookingApi.getReservation(code),
  });
  const reservation = query.data;
  const { msLeft, expired } = useCountdown(reservation?.expires_at);

  const pay = useMutation({
    mutationFn: async () => {
      const payment = await bookingApi.createPayment(code, "online", provider);
      // Sandbox: providers confirm instantly until merchant keys are wired in.
      await bookingApi.mockSuccess(payment.id);
      return payment;
    },
    onSuccess: () => navigate(`/success/${code}`, { viewTransition: true }),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-ink sm:text-[28px]">To‘lov</h1>
        {reservation && (
          <p className="text-[15px] text-muted">
            Bron <span className="tnum font-semibold tracking-wide text-ink">{reservation.public_code}</span>,{" "}
            {seatsWord(reservation.seats.length)}
          </p>
        )}
      </div>

      {query.isLoading && <Skeleton className="h-40 w-full" />}
      {query.isError && <ErrorBox error={query.error} />}
      {pay.isError && <ErrorBox error={pay.error} />}

      {reservation && (
        <>
          {msLeft !== null && (
            <div
              className={`flex items-center gap-3 rounded-panel border px-4 py-3.5 backdrop-blur-md transition-shadow duration-500 ${
                expired ? "border-danger/30 bg-danger-soft/90" : "border-accent/40 bg-accent-soft/90 shadow-glow"
              }`}
            >
              <Timer size={20} weight="bold" className={expired ? "shrink-0 text-danger" : "shrink-0 text-accent-strong"} />
              {expired ? (
                <p className="text-[14px] leading-snug text-ink">
                  Bron muddati tugadi, joylar bo‘shatildi. Reysni qaytadan tanlang.
                </p>
              ) : (
                <p className="text-[14px] leading-snug text-accent-strong">
                  Joylar yana <span className="tnum font-semibold">{formatCountdown(msLeft)}</span> ushlab turiladi
                </p>
              )}
            </div>
          )}

          {reservation.deposit_required && (
            <p className="well rounded-panel px-4 py-3.5 text-[14px] leading-relaxed text-muted">
              Bu bron uchun oldindan to‘lov kerak. Operator siz bilan bog‘lanib, summani tasdiqlaydi.
            </p>
          )}

          <fieldset className="flex flex-col gap-3" disabled={expired}>
            <legend className="mb-1 text-[14px] font-medium text-ink">To‘lov usuli</legend>
            {PROVIDERS.map((p) => {
              const active = provider === p.id;
              return (
                <label
                  key={p.id}
                  className={`glass flex cursor-pointer items-center gap-4 rounded-panel p-4 transition-all duration-300 ease-out ${
                    active
                      ? "border-accent/60 shadow-glow"
                      : "hover:-translate-y-0.5 hover:border-accent/40"
                  } ${expired ? "cursor-not-allowed opacity-50" : ""}`}
                >
                  <input
                    type="radio"
                    name="provider"
                    value={p.id}
                    checked={active}
                    onChange={() => setProvider(p.id)}
                    className="sr-only"
                  />
                  <ProviderMark id={p.id} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[15px] font-semibold text-ink">{p.title}</span>
                    <span className="mt-0.5 block text-[13.5px] leading-relaxed text-muted">{p.body}</span>
                  </span>
                  <span
                    aria-hidden="true"
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                      active ? "border-accent bg-accent text-accent-ink" : "border-line"
                    }`}
                  >
                    {active && <Check size={13} weight="bold" />}
                  </span>
                </label>
              );
            })}

            <div
              aria-disabled="true"
              className="flex items-center gap-4 rounded-panel border border-dashed border-line px-4 py-3.5 opacity-70"
            >
              <span className="well flex h-11 w-11 shrink-0 items-center justify-center rounded-[13px] text-muted">
                <Money size={22} weight="regular" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-semibold text-muted">Naqd pul</span>
                <span className="mt-0.5 block text-[13.5px] text-faint">Haydovchiga to‘lash tez kunda qo‘shiladi.</span>
              </span>
              <span className="rounded-full border border-line px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-faint">
                tez kunda
              </span>
            </div>
          </fieldset>

          <div className="well flex flex-wrap items-center justify-between gap-4 rounded-panel px-4 py-4 sm:px-5">
            <span className="text-[15px] text-muted">To‘lovga</span>
            <Amount
              minor={reservation.total_amount_minor}
              currency={reservation.currency}
              className="text-[22px] font-semibold text-ink"
            />
          </div>

          {expired ? (
            <Link to="/" viewTransition className="no-underline">
              <Button size="lg" block>
                Boshqa reys tanlash
              </Button>
            </Link>
          ) : (
            <Button size="lg" block loading={pay.isPending} onClick={() => pay.mutate()}>
              {pay.isPending ? "To‘lov tekshirilmoqda…" : `${PROVIDERS.find((p) => p.id === provider)?.title} orqali to‘lash`}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
