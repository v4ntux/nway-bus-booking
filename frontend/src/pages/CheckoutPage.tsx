import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import WebApp from "@twa-dev/sdk";
import { bookingApi } from "../api/booking";
import { rememberBookingPhone } from "../api/client";
import { catalogApi } from "../api/catalog";
import { TripStrip } from "../components/TripCard";
import { Amount, Button, EmptyState, ErrorBox, Field, Input, backLinkClass } from "../components/Ui";
import { loadDraft, saveDraft } from "../features/booking/draft";
import { telegramDisplayName, useTelegram } from "../telegram/TelegramProvider";
import { formatPhoneDisplay, phoneToApi, seatsWord } from "../utils/format";

export function CheckoutPage() {
  const navigate = useNavigate();
  const { isTelegram, user, haptic } = useTelegram();
  const draft = loadDraft();
  const tgName = telegramDisplayName(user);
  const [phone, setPhone] = useState(() => formatPhoneDisplay(draft?.phone ?? ""));
  const [names, setNames] = useState<string[]>(() => {
    const fromDraft = draft?.passengers.map((p) => p.first_name) ?? [];
    if (fromDraft.some(Boolean)) return fromDraft;
    if (tgName) return draft?.seatIds.map((_, i) => (i === 0 ? tgName.split(" ")[0] : "")) ?? [];
    return fromDraft;
  });
  const [touched, setTouched] = useState(false);

  const tripQuery = useQuery({
    queryKey: ["trip", draft?.tripId],
    queryFn: () => catalogApi.trip(draft!.tripId),
    enabled: Boolean(draft?.tripId),
  });

  const mutation = useMutation({
    mutationFn: bookingApi.createReservation,
    onSuccess: (reservation) => navigate(`/pay/${reservation.public_code}`, { viewTransition: true }),
  });

  if (!draft) {
    return (
      <EmptyState
        title="Joylar hali tanlanmagan"
        body="Davom etish uchun reysni topib, salondan joy tanlang."
        action={
          <Link to="/" viewTransition className="no-underline">
            <Button>Reys topish</Button>
          </Link>
        }
      />
    );
  }

  const canShareContact = isTelegram && WebApp.isVersionAtLeast("6.9");

  function shareContact() {
    try {
      WebApp.requestContact((granted, result) => {
        if (!granted || !result || result.status !== "sent") return;
        const raw = new URLSearchParams(result.response).get("contact");
        const shared: string = raw ? (JSON.parse(raw).phone_number ?? "") : "";
        if (shared) setPhone(formatPhoneDisplay(shared.startsWith("+") ? shared : `+${shared}`));
      });
    } catch {
      /* Older Telegram client: typing the number still works. */
    }
  }

  const digits = phone.replace(/\D/g, "");
  const phoneValid = digits.length >= 12;
  const missingName = draft.seatIds.some((_, i) => !(names[i] ?? "").trim());
  const trip = tripQuery.data;
  const total = trip ? trip.base_price_minor * draft.seatIds.length : 0;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (!draft || !phoneValid || missingName) return;
    const apiPhone = phoneToApi(phone);
    const passengers = draft.seatIds.map((id, index) => ({
      seat_id: id,
      first_name: names[index].trim(),
    }));
    const requestKey = draft.requestKey ?? crypto.randomUUID();
    saveDraft({ ...draft, phone: apiPhone, passengers, requestKey });
    rememberBookingPhone(apiPhone);
    if (isTelegram) haptic("medium");
    mutation.mutate({
      request_key: requestKey,
      trip_id: draft.tripId,
      seat_ids: draft.seatIds,
      contact_phone: apiPhone,
      passengers,
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <Link to={`/trips/${draft.tripId}/seats`} viewTransition className={backLinkClass}>
        <ArrowLeft size={15} weight="bold" />
        Joylarni o‘zgartirish
      </Link>

      {trip && <TripStrip trip={trip} />}

      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-ink sm:text-[28px]">
          Kim yo‘lga chiqadi
        </h1>
        <p className="text-[15px] text-muted">
          {seatsWord(draft.seatIds.length)}: {draft.seatNumbers.join(", ")}. Ism haydovchi sizni
          ro‘yxatdan topishi uchun kerak.
        </p>
      </div>

      {mutation.isError && <ErrorBox error={mutation.error} />}

      <form onSubmit={onSubmit} className="flex flex-col gap-5">
        <div className="glass rounded-panel p-4 sm:p-5">
          <Field
            label="Aloqa uchun telefon"
            hint="Reys bo‘yicha bog‘lanish uchun. Telegramda chipta shu chatga yuboriladi."
            htmlFor="phone"
            error={touched && !phoneValid ? "Raqamni to‘liq kiriting." : undefined}
          >
            <Input
              name="phone"
              id="phone"
              value={phone}
              onChange={(e) => setPhone(formatPhoneDisplay(e.target.value))}
              placeholder="+998 90 123 45 67"
              inputMode="tel"
              autoComplete="tel"
              className="tnum"
            />
          </Field>
          {canShareContact && (
            <Button type="button" variant="secondary" size="sm" className="mt-3" onClick={shareContact}>
              📱 Telegramdagi raqamni olish
            </Button>
          )}
        </div>

        <div className="glass flex flex-col gap-4 rounded-panel p-4 sm:p-5">
          {draft.seatNumbers.map((number, index) => (
            <Field
              key={draft.seatIds[index]}
              label={`Yo‘lovchi ismi, ${number}-joy`}
              htmlFor={`name-${index}`}
              error={touched && !(names[index] ?? "").trim() ? "Yo‘lovchi ismini kiriting." : undefined}
            >
              <Input
                name={`passenger-${index}`}
                id={`name-${index}`}
                value={names[index] ?? ""}
                onChange={(e) => {
                  const next = [...names];
                  next[index] = e.target.value;
                  setNames(next);
                }}
                placeholder="Pasportdagidek"
                autoComplete={index === 0 ? "given-name" : "off"}
              />
            </Field>
          ))}
        </div>

        <div className="well flex flex-wrap items-center justify-between gap-4 rounded-panel px-4 py-4 sm:px-5">
          <span className="text-[15px] text-muted">To‘lovga</span>
          {trip && (
            <Amount minor={total} currency={trip.currency} className="text-[22px] font-semibold text-ink" />
          )}
        </div>

        <Button
          type="submit"
          size="lg"
          block
          loading={mutation.isPending}
          icon={mutation.isPending ? undefined : <ArrowRight size={17} weight="bold" />}
        >
          {mutation.isPending ? "Joylar band qilinmoqda…" : "To‘lovga o‘tish"}
        </Button>
      </form>
    </div>
  );
}
