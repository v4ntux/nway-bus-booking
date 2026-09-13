import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import { catalogApi } from "../api/catalog";
import { SeatMapView } from "../components/SeatMapView";
import { TripStrip } from "../components/TripCard";
import { Amount, Button, ErrorBox, Skeleton, backLinkClass } from "../components/Ui";
import { saveDraft } from "../features/booking/draft";
import { seatsWord } from "../utils/format";

const LARGE_BOOKING_THRESHOLD = 4;

export function SeatsPage() {
  const { tripId = "" } = useParams();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string[]>([]);
  const tripQuery = useQuery({ queryKey: ["trip", tripId], queryFn: () => catalogApi.trip(tripId) });
  const seatsQuery = useQuery({ queryKey: ["seats", tripId], queryFn: () => catalogApi.seats(tripId) });

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function continueNext() {
    const map = seatsQuery.data;
    if (!map || !tripQuery.data) return;
    const numbers = selected.map(
      (id) => map.cells.find((c) => c.seat?.id === id)?.seat?.seat_number ?? id,
    );
    saveDraft({
      tripId,
      seatIds: selected,
      seatNumbers: numbers,
      passengers: selected.map((id) => ({ seat_id: id, first_name: "" })),
      phone: "",
    });
    navigate("/checkout", { viewTransition: true });
  }

  const trip = tripQuery.data;
  const total = trip ? trip.base_price_minor * selected.length : 0;
  const selectedNumbers = selected
    .map((id) => seatsQuery.data?.cells.find((c) => c.seat?.id === id)?.seat?.seat_number)
    .filter(Boolean);
  const large = selected.length >= LARGE_BOOKING_THRESHOLD;

  return (
    <div className="flex flex-col gap-5 pb-32">
      <Link to="/trips" viewTransition className={backLinkClass}>
        <ArrowLeft size={15} weight="bold" />
        Reyslar ro‘yxatiga
      </Link>

      {(tripQuery.isError || seatsQuery.isError) && (
        <ErrorBox error={tripQuery.error || seatsQuery.error} />
      )}

      {trip && <TripStrip trip={trip} />}
      {tripQuery.isLoading && <Skeleton className="h-24 w-full" />}

      <div className="flex flex-col gap-2">
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-ink sm:text-[28px]">
          Joyingizni tanlang
        </h1>
        {trip && (
          <p className="text-[15px] text-muted">
            <Amount minor={trip.base_price_minor} currency={trip.currency} className="text-ink" /> bir joy
            uchun. Sxemada haydovchi yuqorida, kirish eshigi o‘ng tomonda.
          </p>
        )}
      </div>

      {seatsQuery.isLoading && <Skeleton className="mx-auto h-[720px] w-full max-w-sm rounded-plate" />}
      {seatsQuery.data && (
        <SeatMapView map={seatsQuery.data} selected={selected} onToggle={toggle} />
      )}

      {large && (
        <p className="rounded-panel border border-accent/40 bg-accent-soft/90 px-4 py-3 text-[14px] leading-relaxed text-accent-strong backdrop-blur-md">
          {LARGE_BOOKING_THRESHOLD} va undan ko‘p joyga bronni operator tasdiqlaydi. Rasmiylashtirgandan
          so‘ng u ko‘rsatilgan raqamga qo‘ng‘iroq qiladi.
        </p>
      )}

      {/* Total follows the passenger down the seat map. */}
      <div
        className={`glass-bar fixed inset-x-0 bottom-0 z-20 border-t transition-shadow duration-500 ease-out ${
          selected.length > 0
            ? "border-accent/30 shadow-[0_-18px_48px_-16px_rgb(var(--c-accent)/0.5)]"
            : "border-hairline shadow-[0_-12px_40px_-18px_rgb(var(--c-shadow)/0.25)]"
        }`}
      >
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-3">
          <div className="min-w-0">
            {selected.length === 0 ? (
              <p className="text-[14px] text-muted">Joy tanlanmagan</p>
            ) : (
              <>
                <p className="truncate text-[13px] text-muted">
                  {seatsWord(selected.length)}: {selectedNumbers.join(", ")}
                </p>
                {trip && (
                  <p className="text-[19px] font-semibold leading-tight text-ink">
                    <Amount minor={total} currency={trip.currency} />
                  </p>
                )}
              </>
            )}
          </div>
          <Button
            type="button"
            size="lg"
            disabled={selected.length === 0}
            onClick={continueNext}
            icon={<ArrowRight size={17} weight="bold" />}
          >
            Davom etish
          </Button>
        </div>
      </div>
    </div>
  );
}
