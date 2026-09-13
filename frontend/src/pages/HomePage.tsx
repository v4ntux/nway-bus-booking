import { useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowsDownUp, CalendarBlank, MagnifyingGlass } from "@phosphor-icons/react";
import { catalogApi } from "../api/catalog";
import { CityPicker } from "../components/CityPicker";
import { DatePicker } from "../components/DatePicker";
import { Button, ErrorBox, followSpot } from "../components/Ui";
import { formatLocalDay, toDateInput } from "../utils/format";

function dayOffset(days: number): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + days);
  return d;
}

function shortDate(iso: string) {
  return formatLocalDay(new Date(`${iso}T12:00:00`));
}

export function HomePage() {
  const navigate = useNavigate();
  const citiesQuery = useQuery({ queryKey: ["cities"], queryFn: catalogApi.cities });
  const [origin, setOrigin] = useState("");
  const [dest, setDest] = useState("");
  const [date, setDate] = useState(() => toDateInput(dayOffset(0)));
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [touched, setTouched] = useState(false);

  const cities = citiesQuery.data ?? [];
  const ready = Boolean(origin && dest && date);

  const quickDates = [
    { label: "Bugun", value: toDateInput(dayOffset(0)) },
    { label: "Ertaga", value: toDateInput(dayOffset(1)) },
    { label: shortDate(toDateInput(dayOffset(2))), value: toDateInput(dayOffset(2)) },
  ];
  const onQuickDate = quickDates.some((q) => q.value === date);

  function swap() {
    setOrigin(dest);
    setDest(origin);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (!ready) return;
    navigate(`/trips?origin=${origin}&dest=${dest}&date=${date}`, { viewTransition: true });
  }

  return (
    <div className="flex flex-col gap-8 sm:gap-10">
      <header className="flex max-w-[34ch] flex-col gap-3 animate-fade-rise">
        <h1 className="text-[36px] font-semibold leading-[1.08] tracking-[-0.03em] text-ink sm:text-[50px]">
          Qayerga boramiz?
        </h1>
        <p className="text-[16px] leading-relaxed text-muted sm:text-[17px]">
          Reysni tanlang, avtobusda joyingizni belgilang va Payme, Click yoki karta orqali to‘lang.
        </p>
      </header>

      {citiesQuery.isError && <ErrorBox error={citiesQuery.error} />}

      <form
        onSubmit={onSubmit}
        onPointerMove={followSpot}
        className="glass spot flex flex-col gap-6 rounded-plate p-4 shadow-lift animate-fade-rise sm:p-6"
        style={{ animationDelay: "80ms" }}
      >
        {/* Route: two stacked wells; the swap sits beside them, off the reading line. */}
        <div className="grid grid-cols-[1fr_auto] gap-x-3">
          <div className="flex flex-col gap-3">
            <CityPicker
              label="Qayerdan"
              cities={cities}
              value={origin}
              onChange={setOrigin}
              exclude={dest}
              loading={citiesQuery.isLoading}
              tone="origin"
            />
            <CityPicker
              label="Qayerga"
              cities={cities}
              value={dest}
              onChange={setDest}
              exclude={origin}
              loading={citiesQuery.isLoading}
              tone="destination"
            />
          </div>

          <div className="flex items-center pt-7">
            <button
              type="button"
              onClick={swap}
              disabled={!origin && !dest}
              aria-label="Shaharlarni almashtirish"
              className="glass flex h-12 w-12 items-center justify-center rounded-full text-muted transition-all duration-500 ease-spring hover:rotate-180 hover:border-accent/50 hover:text-ink hover:shadow-glow disabled:opacity-40"
            >
              <ArrowsDownUp size={18} weight="bold" />
            </button>
          </div>
        </div>

        <div className="border-t border-hairline/80 pt-5">
          <span className="mb-2 block text-sm font-medium text-ink">Sayohat sanasi</span>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {quickDates.map((q) => {
              const active = date === q.value;
              return (
                <button
                  key={q.value}
                  type="button"
                  onClick={() => {
                    setDate(q.value);
                    setCalendarOpen(false);
                  }}
                  aria-pressed={active}
                  className={`h-12 rounded-control px-2 text-[14px] font-semibold transition-all duration-300 ease-out ${
                    active ? "btn-sun" : "well text-muted hover:border-accent/40 hover:text-ink"
                  }`}
                >
                  {q.label}
                </button>
              );
            })}

            <button
              type="button"
              onClick={() => setCalendarOpen((o) => !o)}
              aria-expanded={calendarOpen}
              aria-label="Boshqa sanani tanlash"
              className={`flex h-12 items-center justify-center gap-2 rounded-control px-2 text-[14px] font-semibold transition-all duration-300 ease-out ${
                calendarOpen || !onQuickDate ? "btn-sun" : "well text-muted hover:border-accent/40 hover:text-ink"
              }`}
            >
              <CalendarBlank size={17} weight="bold" />
              {!onQuickDate ? <span className="tnum">{shortDate(date)}</span> : <span>Kalendar</span>}
            </button>
          </div>

          {calendarOpen && (
            <div className="mt-3 animate-fade-rise">
              <DatePicker
                value={date}
                onChange={(next) => {
                  setDate(next);
                  setCalendarOpen(false);
                }}
              />
            </div>
          )}
        </div>

        {touched && !ready && (
          <p role="alert" className="text-[13px] font-medium text-danger">
            Jo‘nash shahri, boradigan shahar va sanani tanlang.
          </p>
        )}

        <Button type="submit" size="lg" block icon={<MagnifyingGlass size={18} weight="bold" />}>
          Reyslarni topish
        </Button>
      </form>

      <p className="max-w-[62ch] text-[14px] leading-relaxed text-muted">
        Tanlangan joy 10 daqiqa siz uchun saqlanadi. 4 va undan ko‘p joyga bron operator tomonidan
        telefon orqali tasdiqlanadi.
      </p>
    </div>
  );
}
