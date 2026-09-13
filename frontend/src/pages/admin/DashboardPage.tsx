import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Bus, MapPin, Path, Plus } from "@phosphor-icons/react";
import { adminApi } from "../../api/admin";
import { AdminHeader } from "../../components/Table";
import { ErrorBox, Skeleton } from "../../components/Ui";

function Metric({ label, value, tone = "ink" }: { label: string; value: number; tone?: "ink" | "muted" }) {
  return (
    <div className="flex flex-col gap-1 px-4 py-4 sm:px-5">
      <p className="text-[13px] text-muted">{label}</p>
      <p className={`tnum text-[30px] font-semibold leading-none ${tone === "ink" ? "text-ink" : "text-muted"}`}>
        {value}
      </p>
    </div>
  );
}

/** Something that needs a human. Zero is quiet; anything else is a link. */
function Attention({ label, value, to }: { label: string; value: number; to: string }) {
  if (value === 0) {
    return (
      <div className="flex items-center justify-between gap-3 px-4 py-3.5 sm:px-5">
        <span className="text-[14px] text-muted">{label}</span>
        <span className="tnum text-[15px] text-faint">0</span>
      </div>
    );
  }
  return (
    <Link
      to={to}
      className="group flex items-center justify-between gap-3 px-4 py-3.5 no-underline transition-colors duration-200 hover:bg-surface/50 sm:px-5"
    >
      <span className="text-[14px] font-medium text-ink">{label}</span>
      <span className="flex items-center gap-2">
        <span className="tnum rounded-full bg-accent px-2.5 py-0.5 text-[13px] font-semibold text-accent-ink">
          {value}
        </span>
        <ArrowRight size={15} weight="bold" className="text-muted transition-transform duration-300 group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

const QUICK = [
  { to: "/admin/trips", label: "Reys qo‘shish", icon: Plus },
  { to: "/admin/routes", label: "Yo‘nalishlar", icon: Path },
  { to: "/admin/cities", label: "Shaharlar", icon: MapPin },
  { to: "/admin/buses", label: "Avtobuslar", icon: Bus },
];

export function DashboardPage() {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: adminApi.dashboard });
  const d = query.data;

  return (
    <>
      <AdminHeader title="Umumiy holat" sub="Bugun nima bo‘lmoqda" />
      {query.isError && <ErrorBox error={query.error} />}
      {query.isLoading && <Skeleton className="h-56 w-full" />}

      {d && (
        <div className="grid gap-5 lg:grid-cols-[1fr_minmax(0,320px)]">
          <div className="flex flex-col gap-5">
            <section className="glass grid divide-y divide-hairline/80 rounded-panel sm:grid-cols-2 sm:divide-x sm:divide-y-0">
              <Metric label="Bugungi reyslar" value={d.trips_today} />
              <Metric label="Bugungi yo‘lovchilar" value={d.passengers_today} />
            </section>

            <section className="glass grid divide-y divide-hairline/80 rounded-panel sm:grid-cols-2 sm:divide-x sm:divide-y-0">
              <Metric label="Sotilgan joylar" value={d.sold_seats} />
              <Metric label="Bo‘sh joylar" value={d.free_seats} tone="muted" />
            </section>

            <section className="glass overflow-hidden rounded-panel">
              <h2 className="border-b border-line/80 bg-surface/40 px-4 py-2.5 text-[12px] font-semibold text-muted sm:px-5">
                E’tibor talab qiladi
              </h2>
              <div className="divide-y divide-hairline/80">
                <Attention
                  label="Tasdiqlash kutilmoqda"
                  value={d.pending_approvals}
                  to="/admin/reservations?status=awaiting_admin_approval"
                />
                <Attention label="To‘lanmagan" value={d.unpaid} to="/admin/reservations?status=pending" />
                <Attention label="Katta buyurtmalar" value={d.large_bookings} to="/admin/reservations" />
              </div>
            </section>
          </div>

          <aside className="glass flex flex-col gap-1 self-start rounded-panel p-2">
            <p className="px-3 pb-1 pt-2 text-[12px] font-semibold text-muted">Tez amallar</p>
            {QUICK.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="flex items-center gap-3 rounded-control px-3 py-2.5 text-[14px] font-medium text-ink no-underline transition-colors duration-200 hover:bg-surface/60"
              >
                <Icon size={17} weight="regular" className="text-accent" />
                {label}
              </Link>
            ))}
          </aside>
        </div>
      )}
    </>
  );
}
