import { Link } from "react-router-dom";
import { ArrowRight, Bus } from "@phosphor-icons/react";
import type { Trip } from "../types/api";
import { Amount, Badge, followSpot } from "./Ui";
import { durationBetween, formatClock, formatDayLabel, formatDuration, seatsWord } from "../utils/format";

/*
 * The signature of this product: a departure-board row.
 * Two clocks in tabular mono, joined by the road between them, with the
 * travel time sitting on that road. Everything else is secondary.
 */

export function RouteLine({
  departure,
  arrival,
  originName,
  destinationName,
  originZone,
  destinationZone,
  size = "lg",
}: {
  departure: string;
  arrival: string;
  originName: string;
  destinationName: string;
  originZone?: string;
  destinationZone?: string;
  size?: "sm" | "lg";
}) {
  const minutes = durationBetween(departure, arrival);
  const big = size === "lg";

  return (
    <div className="flex items-start gap-3 sm:gap-5">
      <div className="min-w-0 shrink-0">
        <p className={`tnum font-semibold leading-none text-ink ${big ? "text-[30px] sm:text-[38px]" : "text-xl"}`}>
          {formatClock(departure, originZone)}
        </p>
        <p className={`mt-1.5 truncate font-medium text-ink ${big ? "text-[15px]" : "text-[13px]"}`}>
          {originName}
        </p>
        <p className="mt-0.5 text-[13px] text-muted">{formatDayLabel(departure, originZone)}</p>
      </div>

      {/* the road */}
      <div className={`relative flex min-w-0 flex-1 flex-col items-center ${big ? "pt-4 sm:pt-5" : "pt-2"}`}>
        <div className="relative flex w-full items-center gap-1.5">
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 shrink-0 rounded-full bg-accent shadow-[0_0_10px_rgb(var(--c-accent)/0.7)]"
          />
          <span aria-hidden="true" className="relative h-px min-w-0 flex-1 overflow-hidden bg-line">
            {big && <span className="road-light" />}
          </span>
          <span
            aria-hidden="true"
            className="h-2.5 w-2.5 shrink-0 rounded-full bg-sky shadow-[0_0_10px_rgb(var(--c-sky)/0.7)]"
          />
        </div>
        <p className="mt-1.5 whitespace-nowrap text-[12px] font-medium text-muted sm:text-[13px]">
          {formatDuration(minutes)}
        </p>
      </div>

      <div className="min-w-0 shrink-0 text-right">
        <p className={`tnum font-semibold leading-none text-ink ${big ? "text-[30px] sm:text-[38px]" : "text-xl"}`}>
          {formatClock(arrival, destinationZone)}
        </p>
        <p className={`mt-1.5 truncate font-medium text-ink ${big ? "text-[15px]" : "text-[13px]"}`}>
          {destinationName}
        </p>
        <p className="mt-0.5 text-[13px] text-muted">{formatDayLabel(arrival, destinationZone)}</p>
      </div>
    </div>
  );
}

export function TripCard({ trip, index = 0 }: { trip: Trip; index?: number }) {
  const origin = trip.route?.origin_city;
  const destination = trip.route?.destination_city;
  const left = trip.available_seats ?? 0;
  const scarce = left > 0 && left <= 5;

  return (
    <li
      className="group glass glass-lift spot animate-fade-rise rounded-panel"
      style={{ animationDelay: `${Math.min(index, 8) * 45}ms` }}
      onPointerMove={followSpot}
    >
      <div className="p-4 sm:p-5">
        <RouteLine
          departure={trip.departure_datetime}
          arrival={trip.estimated_arrival_datetime}
          originName={origin?.name ?? "-"}
          destinationName={destination?.name ?? "-"}
          originZone={origin?.timezone}
          destinationZone={destination?.timezone}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline/80 px-4 py-3.5 sm:px-5">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {trip.bus?.model && (
            <span className="inline-flex items-center gap-1.5 text-[13px] text-muted">
              <Bus size={15} weight="regular" className="shrink-0" />
              <span className="truncate">{trip.bus.model}</span>
              {trip.bus.registration_number && (
                <span className="tnum text-faint">{trip.bus.registration_number}</span>
              )}
            </span>
          )}
          {left > 0 ? (
            <Badge tone={scarce ? "accent" : "positive"}>
              {scarce ? `${seatsWord(left)} qoldi` : `${seatsWord(left)} bo‘sh`}
            </Badge>
          ) : (
            <Badge tone="danger">joy yo‘q</Badge>
          )}
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          <Amount
            minor={trip.base_price_minor}
            currency={trip.currency}
            className="text-[19px] font-semibold text-ink sm:text-[21px]"
          />
          {left > 0 ? (
            <Link
              to={`/trips/${trip.id}/seats`}
              viewTransition
              className="btn-sun inline-flex h-11 items-center gap-2 rounded-control px-4 text-[15px] font-semibold no-underline transition-all duration-300 ease-out hover:-translate-y-0.5 active:translate-y-px"
            >
              Joy tanlash
              <ArrowRight size={16} weight="bold" className="transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>
          ) : (
            <span className="text-[15px] text-faint">Sotilgan</span>
          )}
        </div>
      </div>
    </li>
  );
}

/** Compact trip header carried through seats, checkout and payment. */
export function TripStrip({ trip }: { trip: Trip }) {
  const origin = trip.route?.origin_city;
  const destination = trip.route?.destination_city;
  return (
    <div className="glass rounded-panel px-4 py-3.5">
      <RouteLine
        size="sm"
        departure={trip.departure_datetime}
        arrival={trip.estimated_arrival_datetime}
        originName={origin?.name ?? "-"}
        destinationName={destination?.name ?? "-"}
        originZone={origin?.timezone}
        destinationZone={destination?.timezone}
      />
    </div>
  );
}
