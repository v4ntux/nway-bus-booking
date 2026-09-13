import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ArrowsLeftRight, PencilSimple, Plus, Prohibit } from "@phosphor-icons/react";
import { adminApi } from "../../api/admin";
import {
  BulkBar,
  FilterBar,
  RowCheckbox,
  SelectAllCheckbox,
  matchesQuery,
  useRowSelection,
} from "../../components/AdminFilters";
import { Dialog } from "../../components/Dialog";
import {
  AdminHeader,
  RowAction,
  StatusBadge,
  TRIP_STATUS_UZ,
  Table,
  TableEmpty,
  TableSkeleton,
  Td,
  Th,
  Tr,
} from "../../components/Table";
import { Amount, Button, ErrorBox, Field, Input, Select } from "../../components/Ui";
import { formatClock, formatDayLabel } from "../../utils/format";
import type { Bus, Route, Trip, TripCreateIn, TripPatchIn } from "../../types/api";

/** ISO (UTC) -> value for <input type="datetime-local"> in the operator's zone. */
function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const EDITABLE_STATUSES = ["draft", "scheduled", "boarding", "departed", "completed"];

function CreateForm({
  routes,
  buses,
  pending,
  error,
  onSubmit,
}: {
  routes: Route[];
  buses: Bus[];
  pending: boolean;
  error: unknown;
  onSubmit: (body: TripCreateIn) => void;
}) {
  const [routeId, setRouteId] = useState("");
  const [busId, setBusId] = useState("");
  const [when, setWhen] = useState("");
  // Operators think in som. The API takes hundredths.
  const [price, setPrice] = useState("180000");
  const [boarding, setBoarding] = useState("");
  const [arrival, setArrival] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({
      route_id: routeId,
      bus_id: busId,
      departure_datetime: new Date(when).toISOString(),
      base_price_minor: Math.round(Number(price) * 100),
      boarding_location: boarding.trim() || null,
      destination_location: arrival.trim() || null,
    });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {error != null && <ErrorBox error={error} />}
      <Field label="Yo‘nalish" htmlFor="trip-route">
        <Select id="trip-route" value={routeId} onChange={(e) => setRouteId(e.target.value)} required>
          <option value="">Yo‘nalishni tanlang</option>
          {routes
            .filter((r) => r.active)
            .map((r) => (
              <option key={r.id} value={r.id}>
                {r.origin_city?.name} → {r.destination_city?.name}
              </option>
            ))}
        </Select>
      </Field>
      <Field label="Avtobus" htmlFor="trip-bus">
        <Select id="trip-bus" value={busId} onChange={(e) => setBusId(e.target.value)} required>
          <option value="">Avtobusni tanlang</option>
          {buses
            .filter((b) => b.active)
            .map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}, {b.seat_count} joy, {b.registration_number}
              </option>
            ))}
        </Select>
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Jo‘nash vaqti" htmlFor="trip-when">
          <Input id="trip-when" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className="tnum" required />
        </Field>
        <Field label="Joy narxi, so‘m" htmlFor="trip-price">
          <Input id="trip-price" value={price} onChange={(e) => setPrice(e.target.value)} inputMode="numeric" className="tnum" required />
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Chiqish joyi" hint="Masalan, Toshkent avtovokzali" htmlFor="trip-boarding">
          <Input id="trip-boarding" value={boarding} onChange={(e) => setBoarding(e.target.value)} />
        </Field>
        <Field label="Yetib borish joyi" htmlFor="trip-arrival">
          <Input id="trip-arrival" value={arrival} onChange={(e) => setArrival(e.target.value)} />
        </Field>
      </div>
      <Button type="submit" size="lg" block loading={pending} icon={<Plus size={16} weight="bold" />}>
        Reys yaratish
      </Button>
    </form>
  );
}

function EditForm({
  trip,
  pending,
  error,
  onSubmit,
}: {
  trip: Trip;
  pending: boolean;
  error: unknown;
  onSubmit: (body: TripPatchIn) => void;
}) {
  const [when, setWhen] = useState(toLocalInput(trip.departure_datetime));
  const [price, setPrice] = useState(String(trip.base_price_minor / 100));
  const [status, setStatus] = useState(trip.status);
  const [boarding, setBoarding] = useState(trip.boarding_location ?? "");
  const [arrival, setArrival] = useState(trip.destination_location ?? "");

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({
      departure_datetime: new Date(when).toISOString(),
      base_price_minor: Math.round(Number(price) * 100),
      status,
      boarding_location: boarding.trim(),
      destination_location: arrival.trim(),
    });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {error != null && <ErrorBox error={error} />}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Jo‘nash vaqti" hint="Yetib borish vaqti avtomatik hisoblanadi" htmlFor="e-when">
          <Input id="e-when" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} className="tnum" required />
        </Field>
        <Field label="Joy narxi, so‘m" htmlFor="e-price">
          <Input id="e-price" value={price} onChange={(e) => setPrice(e.target.value)} inputMode="numeric" className="tnum" required />
        </Field>
      </div>
      <Field label="Holat" htmlFor="e-status">
        <Select id="e-status" value={status} onChange={(e) => setStatus(e.target.value)}>
          {EDITABLE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {TRIP_STATUS_UZ[s]?.label ?? s}
            </option>
          ))}
        </Select>
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Chiqish joyi" htmlFor="e-boarding">
          <Input id="e-boarding" value={boarding} onChange={(e) => setBoarding(e.target.value)} />
        </Field>
        <Field label="Yetib borish joyi" htmlFor="e-arrival">
          <Input id="e-arrival" value={arrival} onChange={(e) => setArrival(e.target.value)} />
        </Field>
      </div>
      <Button type="submit" size="lg" block loading={pending}>
        Saqlash
      </Button>
    </form>
  );
}

function ChangeBusForm({
  trip,
  buses,
  pending,
  error,
  onSubmit,
}: {
  trip: Trip;
  buses: Bus[];
  pending: boolean;
  error: unknown;
  onSubmit: (busId: string) => void;
}) {
  const [busId, setBusId] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(busId);
      }}
      className="flex flex-col gap-4"
    >
      {error != null && <ErrorBox error={error} />}
      <p className="text-[14px] leading-relaxed text-muted">
        Hozir: <span className="font-medium text-ink">{trip.bus?.name}</span>. Yangi avtobusda kamida{" "}
        {(trip.bus?.seat_count ?? 0) - (trip.available_seats ?? 0)} ta sotilgan joy uchun o‘rin bo‘lishi kerak.
      </p>
      <Field label="Yangi avtobus" htmlFor="cb-bus">
        <Select id="cb-bus" value={busId} onChange={(e) => setBusId(e.target.value)} required>
          <option value="">Avtobusni tanlang</option>
          {buses
            .filter((b) => b.active && b.id !== trip.bus_id)
            .map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}, {b.seat_count} joy
              </option>
            ))}
        </Select>
      </Field>
      <Button type="submit" size="lg" block loading={pending}>
        Avtobusni almashtirish
      </Button>
    </form>
  );
}

type Modal = { kind: "new" } | { kind: "edit"; trip: Trip } | { kind: "bus"; trip: Trip } | null;

export function TripsPage() {
  const client = useQueryClient();
  const trips = useQuery({ queryKey: ["admin-trips"], queryFn: adminApi.trips });
  const routes = useQuery({ queryKey: ["admin-routes"], queryFn: adminApi.routes });
  const buses = useQuery({ queryKey: ["admin-buses"], queryFn: adminApi.buses });
  const [modal, setModal] = useState<Modal>(null);
  const [showPast, setShowPast] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const now = Date.now();
  const rows = useMemo(() => {
    return (trips.data ?? []).filter((t) => {
      if (!showPast && new Date(t.estimated_arrival_datetime).getTime() <= now - 6 * 3600_000) return false;
      if (status && t.status !== status) return false;
      return matchesQuery(
        [
          t.route?.origin_city?.name,
          t.route?.destination_city?.name,
          t.bus?.name,
          t.bus?.registration_number,
          t.status,
        ],
        search,
      );
    });
  }, [trips.data, showPast, status, search, now]);

  const cancellable = useMemo(
    () => rows.filter((t) => t.status !== "cancelled" && t.status !== "completed").map((t) => t.id),
    [rows],
  );
  const selection = useRowSelection(cancellable);

  const refresh = () => {
    client.invalidateQueries({ queryKey: ["admin-trips"] });
    setModal(null);
    selection.clear();
  };
  const create = useMutation({ mutationFn: adminApi.createTrip, onSuccess: refresh });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: TripPatchIn }) => adminApi.patchTrip(id, body),
    onSuccess: refresh,
  });
  const changeBus = useMutation({
    mutationFn: ({ id, busId }: { id: string; busId: string }) => adminApi.changeBus(id, busId),
    onSuccess: refresh,
  });
  const cancel = useMutation({
    mutationFn: async (ids: string[]) => {
      for (const id of ids) await adminApi.cancelTrip(id);
    },
    onSuccess: refresh,
  });

  return (
    <>
      <AdminHeader
        title="Reyslar"
        sub="Jadval, narxlar va avtobuslar"
        action={
          <Button onClick={() => setModal({ kind: "new" })} icon={<Plus size={16} weight="bold" />}>
            Reys qo‘shish
          </Button>
        }
      />

      {trips.isError && <ErrorBox error={trips.error} />}
      {cancel.isError && <ErrorBox error={cancel.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Shahar, avtobus, raqam…"
        status={status}
        onStatus={setStatus}
        statusOptions={Object.entries(TRIP_STATUS_UZ).map(([value, v]) => ({ value, label: v.label }))}
        resultCount={rows.length}
        totalCount={trips.data?.length}
      >
        <label className="flex items-center gap-2 text-[13.5px] text-muted">
          <input type="checkbox" checked={showPast} onChange={(e) => setShowPast(e.target.checked)} className="h-4 w-4" />
          O‘tganlar ham
        </label>
      </FilterBar>

      <BulkBar
        selectedCount={selection.count}
        filteredCount={cancellable.length}
        pending={cancel.isPending}
        onDeleteSelected={() => cancel.mutate(selection.selectedIds)}
        onDeleteFiltered={() => cancel.mutate(cancellable)}
        deleteLabel="Tanlanganlarni bekor qilish"
        deleteAllLabel="Filtrdagilarni bekor qilish"
      />

      {trips.isLoading ? (
        <TableSkeleton cols={7} />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th className="w-10">
                <SelectAllCheckbox
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggle={selection.toggleAll}
                  disabled={cancellable.length === 0}
                />
              </Th>
              <Th>Jo‘nash</Th>
              <Th>Yo‘nalish</Th>
              <Th>Avtobus</Th>
              <Th>Holat</Th>
              <Th className="text-right">Bo‘sh</Th>
              <Th className="text-right">Narx</Th>
              <Th className="text-right">Amallar</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <TableEmpty colSpan={8}>Reyslar yo‘q.</TableEmpty>}
            {rows.map((t) => {
              const zone = t.route?.origin_city?.timezone;
              const closed = t.status === "cancelled" || t.status === "completed";
              return (
                <Tr key={t.id} className={closed ? "opacity-60" : ""}>
                  <Td>
                    {!closed ? (
                      <RowCheckbox
                        checked={selection.isSelected(t.id)}
                        onChange={() => selection.toggle(t.id)}
                        label="Tanlash"
                      />
                    ) : (
                      <span className="inline-block w-4" />
                    )}
                  </Td>
                  <Td className="whitespace-nowrap">
                    <span className="tnum font-medium">{formatClock(t.departure_datetime, zone)}</span>
                    <span className="ml-2 text-[13px] text-muted">{formatDayLabel(t.departure_datetime, zone)}</span>
                  </Td>
                  <Td>
                    <span className="flex items-center gap-2 whitespace-nowrap">
                      {t.route?.origin_city?.name ?? "-"}
                      <ArrowRight size={13} weight="bold" className="shrink-0 text-accent" />
                      {t.route?.destination_city?.name ?? "-"}
                    </span>
                  </Td>
                  <Td className="whitespace-nowrap text-muted">
                    {t.bus?.name}
                    <span className="tnum ml-2 text-[12px] text-faint">{t.bus?.registration_number}</span>
                  </Td>
                  <Td>
                    <StatusBadge status={t.status} kind="trip" />
                  </Td>
                  <Td className="tnum text-right">
                    {t.available_seats ?? "-"}
                    <span className="text-faint">/{t.bus?.seat_count}</span>
                  </Td>
                  <Td className="whitespace-nowrap text-right">
                    <Amount minor={t.base_price_minor} currency={t.currency} className="font-medium" />
                  </Td>
                  <Td className="text-right">
                    {!closed && (
                      <div className="flex justify-end gap-1.5">
                        <RowAction onClick={() => setModal({ kind: "edit", trip: t })}>
                          <PencilSimple size={14} weight="bold" />
                          Tahrirlash
                        </RowAction>
                        <RowAction onClick={() => setModal({ kind: "bus", trip: t })}>
                          <ArrowsLeftRight size={14} weight="bold" />
                          Avtobus
                        </RowAction>
                        <RowAction
                          tone="danger"
                          disabled={cancel.isPending}
                          onClick={() => {
                            if (window.confirm("Reys bekor qilinsinmi? Barcha bronlar bekor bo‘ladi.")) {
                              cancel.mutate([t.id]);
                            }
                          }}
                        >
                          <Prohibit size={14} weight="bold" />
                          Bekor qilish
                        </RowAction>
                      </div>
                    )}
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
      )}

      <Dialog
        open={modal !== null}
        onClose={() => setModal(null)}
        title={modal?.kind === "new" ? "Yangi reys" : modal?.kind === "edit" ? "Reysni tahrirlash" : "Avtobusni almashtirish"}
        wide={modal?.kind !== "bus"}
      >
        {modal?.kind === "new" && (
          <CreateForm
            routes={routes.data ?? []}
            buses={buses.data ?? []}
            pending={create.isPending}
            error={create.error}
            onSubmit={(body) => create.mutate(body)}
          />
        )}
        {modal?.kind === "edit" && (
          <EditForm
            key={modal.trip.id}
            trip={modal.trip}
            pending={patch.isPending}
            error={patch.error}
            onSubmit={(body) => patch.mutate({ id: modal.trip.id, body })}
          />
        )}
        {modal?.kind === "bus" && (
          <ChangeBusForm
            key={modal.trip.id}
            trip={modal.trip}
            buses={buses.data ?? []}
            pending={changeBus.isPending}
            error={changeBus.error}
            onSubmit={(busId) => changeBus.mutate({ id: modal.trip.id, busId })}
          />
        )}
      </Dialog>
    </>
  );
}
