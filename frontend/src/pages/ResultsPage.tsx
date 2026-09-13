import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, CalendarX } from "@phosphor-icons/react";
import { catalogApi } from "../api/catalog";
import { TripCard } from "../components/TripCard";
import { Button, EmptyState, ErrorBox, Skeleton, backLinkClass } from "../components/Ui";
import { formatDayLabel, tripsWord } from "../utils/format";

type Sort = "time" | "price";

function ResultsSkeleton() {
  return (
    <ul className="flex flex-col gap-3">
      {[0, 1, 2].map((i) => (
        <li key={i} className="glass rounded-panel">
          <div className="flex items-start gap-5 p-5">
            <div className="flex flex-col gap-2">
              <Skeleton className="h-9 w-20" />
              <Skeleton className="h-4 w-24" />
            </div>
            <Skeleton className="mt-4 h-px flex-1" />
            <div className="flex flex-col items-end gap-2">
              <Skeleton className="h-9 w-20" />
              <Skeleton className="h-4 w-24" />
            </div>
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-hairline/80 px-5 py-3.5">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-11 w-40" />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ResultsPage() {
  const [params] = useSearchParams();
  const origin = params.get("origin") ?? "";
  const dest = params.get("dest") ?? "";
  const date = params.get("date") ?? "";
  const [sort, setSort] = useState<Sort>("time");

  const query = useQuery({
    queryKey: ["trips", origin, dest, date],
    queryFn: () => catalogApi.searchTrips(origin, dest, date),
    enabled: Boolean(origin && dest && date),
  });

  const trips = useMemo(() => {
    const items = [...(query.data?.items ?? [])];
    items.sort((a, b) =>
      sort === "price"
        ? a.base_price_minor - b.base_price_minor
        : a.departure_datetime.localeCompare(b.departure_datetime),
    );
    return items;
  }, [query.data, sort]);

  const first = trips[0];
  const heading = first
    ? `${first.route?.origin_city?.name} - ${first.route?.destination_city?.name}`
    : "Reyslar";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <Link to="/" viewTransition className={backLinkClass}>
          <ArrowLeft size={15} weight="bold" />
          Orqaga
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-[26px] font-semibold leading-tight tracking-[-0.02em] text-ink sm:text-[32px]">
              {heading}
            </h1>
            <p className="mt-1 text-[15px] text-muted">
              {date && formatDayLabel(`${date}T12:00:00Z`)}
              {trips.length > 0 && `, ${tripsWord(trips.length)}`}
            </p>
          </div>

          {trips.length > 1 && (
            <div
              role="group"
              aria-label="Saralash"
              className="glass flex items-center gap-0.5 rounded-full p-0.5"
            >
              {(
                [
                  ["time", "Vaqt bo‘yicha"],
                  ["price", "Narx bo‘yicha"],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setSort(key)}
                  aria-pressed={sort === key}
                  className={`h-8 rounded-full px-3.5 text-[13px] font-semibold transition-all duration-300 ease-out ${
                    sort === key ? "btn-sun" : "text-muted hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {query.isError && <ErrorBox error={query.error} />}
      {query.isLoading && <ResultsSkeleton />}

      {query.isSuccess && trips.length === 0 && (
        <EmptyState
          icon={<CalendarX size={40} weight="light" />}
          title="Bu sanaga reys yo‘q"
          body="Qo‘shni kunni yoki boshqa yo‘nalishni sinab ko‘ring."
          action={
            <Link to="/" viewTransition className="no-underline">
              <Button variant="secondary">Qidiruvni o‘zgartirish</Button>
            </Link>
          }
        />
      )}

      {trips.length > 0 && (
        <ul className="flex flex-col gap-3">
          {trips.map((trip, i) => (
            <TripCard key={trip.id} trip={trip} index={i} />
          ))}
        </ul>
      )}
    </div>
  );
}
