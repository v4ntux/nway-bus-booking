import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, PencilSimple, Plus, Power } from "@phosphor-icons/react";
import { adminApi } from "../../api/admin";
import {
  ACTIVE_FILTER,
  BulkBar,
  FilterBar,
  RowCheckbox,
  SelectAllCheckbox,
  filterByActive,
  matchesQuery,
  useRowSelection,
} from "../../components/AdminFilters";
import { Dialog } from "../../components/Dialog";
import { ActiveBadge, AdminHeader, RowAction, Table, TableEmpty, TableSkeleton, Td, Th, Tr } from "../../components/Table";
import { Button, ErrorBox, Field, Input, Select } from "../../components/Ui";
import { formatDuration } from "../../utils/format";
import type { City, Route, RouteIn } from "../../types/api";

const EMPTY: RouteIn = {
  origin_city_id: "",
  destination_city_id: "",
  estimated_duration_minutes: 300,
  distance_km: 300,
  description: "",
  active: true,
};

function RouteForm({
  initial,
  cities,
  pending,
  error,
  onSubmit,
}: {
  initial: RouteIn;
  cities: City[];
  pending: boolean;
  error: unknown;
  onSubmit: (body: RouteIn) => void;
}) {
  const [form, setForm] = useState<RouteIn>(initial);
  const [hours, setHours] = useState(String(Math.floor(initial.estimated_duration_minutes / 60)));
  const [mins, setMins] = useState(String(initial.estimated_duration_minutes % 60));
  const set = <K extends keyof RouteIn>(key: K, value: RouteIn[K]) => setForm((f) => ({ ...f, [key]: value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({
      ...form,
      estimated_duration_minutes: Number(hours) * 60 + Number(mins),
      description: form.description?.trim() || null,
    });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {error != null && <ErrorBox error={error} />}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Qayerdan" htmlFor="route-origin">
          <Select id="route-origin" value={form.origin_city_id} onChange={(e) => set("origin_city_id", e.target.value)} required>
            <option value="">Shaharni tanlang</option>
            {cities
              .filter((c) => c.id !== form.destination_city_id)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </Select>
        </Field>
        <Field label="Qayerga" htmlFor="route-dest">
          <Select id="route-dest" value={form.destination_city_id} onChange={(e) => set("destination_city_id", e.target.value)} required>
            <option value="">Shaharni tanlang</option>
            {cities
              .filter((c) => c.id !== form.origin_city_id)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </Select>
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Yo‘l vaqti, soat" htmlFor="route-h">
          <Input id="route-h" value={hours} onChange={(e) => setHours(e.target.value)} inputMode="numeric" className="tnum" required />
        </Field>
        <Field label="Daqiqa" htmlFor="route-m">
          <Input id="route-m" value={mins} onChange={(e) => setMins(e.target.value)} inputMode="numeric" className="tnum" required />
        </Field>
        <Field label="Masofa, km" htmlFor="route-km">
          <Input
            id="route-km"
            value={String(form.distance_km)}
            onChange={(e) => set("distance_km", Number(e.target.value) || 0)}
            inputMode="numeric"
            className="tnum"
            required
          />
        </Field>
      </div>
      <Field label="Izoh" hint="Masalan, qaysi avtovokzaldan jo‘naydi" htmlFor="route-desc">
        <Input id="route-desc" value={form.description ?? ""} onChange={(e) => set("description", e.target.value)} />
      </Field>
      <label className="flex items-center gap-3 text-[14px] text-ink">
        <input type="checkbox" checked={form.active} onChange={(e) => set("active", e.target.checked)} className="h-4 w-4" />
        Faol (reys qo‘yish mumkin)
      </label>
      <Button type="submit" size="lg" block loading={pending}>
        Saqlash
      </Button>
    </form>
  );
}

export function RoutesPage() {
  const client = useQueryClient();
  const routes = useQuery({ queryKey: ["admin-routes"], queryFn: adminApi.routes });
  const cities = useQuery({ queryKey: ["admin-cities"], queryFn: adminApi.cities });
  const [editing, setEditing] = useState<Route | "new" | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const rows = useMemo(() => {
    const all = filterByActive(routes.data ?? [], status);
    return all.filter((r) =>
      matchesQuery([r.origin_city?.name, r.destination_city?.name, r.description, r.distance_km], search),
    );
  }, [routes.data, search, status]);

  const removable = useMemo(() => rows.filter((r) => r.active).map((r) => r.id), [rows]);
  const selection = useRowSelection(removable);

  const refresh = () => {
    client.invalidateQueries({ queryKey: ["admin-routes"] });
    setEditing(null);
    selection.clear();
  };
  const create = useMutation({ mutationFn: adminApi.createRoute, onSuccess: refresh });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: RouteIn }) => adminApi.patchRoute(id, body),
    onSuccess: refresh,
  });
  const deactivate = useMutation({
    mutationFn: async (ids: string[]) => {
      for (const id of ids) await adminApi.deactivateRoute(id);
    },
    onSuccess: refresh,
  });

  return (
    <>
      <AdminHeader
        title="Yo‘nalishlar"
        sub="Reyslar qo‘yiladigan shahar juftliklari"
        action={
          <Button onClick={() => setEditing("new")} icon={<Plus size={16} weight="bold" />}>
            Yo‘nalish qo‘shish
          </Button>
        }
      />

      {routes.isError && <ErrorBox error={routes.error} />}
      {deactivate.isError && <ErrorBox error={deactivate.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Shahar, izoh…"
        status={status}
        onStatus={setStatus}
        statusOptions={ACTIVE_FILTER}
        resultCount={rows.length}
        totalCount={routes.data?.length}
      />

      <BulkBar
        selectedCount={selection.count}
        filteredCount={removable.length}
        pending={deactivate.isPending}
        onDeleteSelected={() => deactivate.mutate(selection.selectedIds)}
        onDeleteFiltered={() => deactivate.mutate(removable)}
      />

      {routes.isLoading ? (
        <TableSkeleton cols={5} />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th className="w-10">
                <SelectAllCheckbox
                  allSelected={selection.allSelected}
                  someSelected={selection.someSelected}
                  onToggle={selection.toggleAll}
                  disabled={removable.length === 0}
                />
              </Th>
              <Th>Yo‘nalish</Th>
              <Th className="text-right">Yo‘lda</Th>
              <Th className="text-right">Masofa</Th>
              <Th>Holat</Th>
              <Th className="text-right">Amallar</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <TableEmpty colSpan={6}>Hech narsa topilmadi.</TableEmpty>}
            {rows.map((r) => (
              <Tr key={r.id}>
                <Td>
                  {r.active ? (
                    <RowCheckbox
                      checked={selection.isSelected(r.id)}
                      onChange={() => selection.toggle(r.id)}
                      label="Tanlash"
                    />
                  ) : (
                    <span className="inline-block w-4" />
                  )}
                </Td>
                <Td>
                  <span className="flex items-center gap-2 font-medium">
                    {r.origin_city?.name ?? "-"}
                    <ArrowRight size={14} weight="bold" className="shrink-0 text-accent" />
                    {r.destination_city?.name ?? "-"}
                  </span>
                  {r.description && <span className="mt-0.5 block text-[12.5px] text-muted">{r.description}</span>}
                </Td>
                <Td className="whitespace-nowrap text-right text-muted">{formatDuration(r.estimated_duration_minutes)}</Td>
                <Td className="tnum whitespace-nowrap text-right">{r.distance_km} km</Td>
                <Td>
                  <ActiveBadge active={r.active} />
                </Td>
                <Td className="text-right">
                  <div className="flex justify-end gap-1.5">
                    <RowAction onClick={() => setEditing(r)}>
                      <PencilSimple size={14} weight="bold" />
                      Tahrirlash
                    </RowAction>
                    {r.active && (
                      <RowAction
                        tone="danger"
                        onClick={() => deactivate.mutate([r.id])}
                        disabled={deactivate.isPending}
                      >
                        <Power size={14} weight="bold" />
                        O‘chirish
                      </RowAction>
                    )}
                  </div>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <Dialog
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing === "new" ? "Yangi yo‘nalish" : "Yo‘nalishni tahrirlash"}
        wide
      >
        {editing !== null && (
          <RouteForm
            key={editing === "new" ? "new" : editing.id}
            cities={cities.data ?? []}
            initial={
              editing === "new"
                ? EMPTY
                : {
                    origin_city_id: editing.origin_city_id,
                    destination_city_id: editing.destination_city_id,
                    estimated_duration_minutes: editing.estimated_duration_minutes,
                    distance_km: editing.distance_km,
                    description: editing.description ?? "",
                    active: editing.active,
                  }
            }
            pending={create.isPending || patch.isPending}
            error={create.error ?? patch.error}
            onSubmit={(body) => (editing === "new" ? create.mutate(body) : patch.mutate({ id: editing.id, body }))}
          />
        )}
      </Dialog>
    </>
  );
}
