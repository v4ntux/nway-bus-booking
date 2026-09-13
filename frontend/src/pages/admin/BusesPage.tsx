import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Armchair, PencilSimple, Plus, Power } from "@phosphor-icons/react";
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
import { Button, ErrorBox, Field, Input } from "../../components/Ui";
import type { Bus, BusIn } from "../../types/api";

const EMPTY: BusIn = {
  name: "",
  registration_number: "",
  model: "",
  seat_count: 50,
  layout_type: "2+2",
  active: true,
};

function BusForm({
  initial,
  pending,
  error,
  onSubmit,
}: {
  initial: BusIn;
  pending: boolean;
  error: unknown;
  onSubmit: (body: BusIn) => void;
}) {
  const [form, setForm] = useState<BusIn>(initial);
  const set = <K extends keyof BusIn>(key: K, value: BusIn[K]) => setForm((f) => ({ ...f, [key]: value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({
      ...form,
      name: form.name.trim(),
      model: form.model.trim(),
      registration_number: form.registration_number.trim().toUpperCase(),
    });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {error != null && <ErrorBox error={error} />}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nomi" hint="Ichki nom, masalan «Yutong 1»" htmlFor="bus-name">
          <Input id="bus-name" value={form.name} onChange={(e) => set("name", e.target.value)} required />
        </Field>
        <Field label="Davlat raqami" htmlFor="bus-plate">
          <Input
            id="bus-plate"
            value={form.registration_number}
            onChange={(e) => set("registration_number", e.target.value.toUpperCase())}
            placeholder="01 A 123 AA"
            className="tnum"
            required
          />
        </Field>
      </div>
      <Field label="Model" htmlFor="bus-model">
        <Input id="bus-model" value={form.model} onChange={(e) => set("model", e.target.value)} placeholder="Yutong ZK6122H9" required />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Joylar soni" htmlFor="bus-seats">
          <Input
            id="bus-seats"
            value={String(form.seat_count)}
            onChange={(e) => set("seat_count", Number(e.target.value) || 0)}
            inputMode="numeric"
            className="tnum"
            required
          />
        </Field>
        <Field label="Salon turi" hint="Ma’lumot uchun: 2+2, 2+1" htmlFor="bus-layout">
          <Input id="bus-layout" value={form.layout_type} onChange={(e) => set("layout_type", e.target.value)} />
        </Field>
      </div>
      <label className="flex items-center gap-3 text-[14px] text-ink">
        <input type="checkbox" checked={form.active} onChange={(e) => set("active", e.target.checked)} className="h-4 w-4" />
        Faol (reyslarga qo‘yish mumkin)
      </label>
      <Button type="submit" size="lg" block loading={pending}>
        Saqlash
      </Button>
    </form>
  );
}

export function BusesPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["admin-buses"], queryFn: adminApi.buses });
  const [editing, setEditing] = useState<Bus | "new" | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const rows = useMemo(() => {
    const all = filterByActive(query.data ?? [], status);
    return all.filter((b) => matchesQuery([b.name, b.model, b.registration_number, b.seat_count], search));
  }, [query.data, search, status]);

  const removable = useMemo(() => rows.filter((b) => b.active).map((b) => b.id), [rows]);
  const selection = useRowSelection(removable);

  const refresh = () => {
    client.invalidateQueries({ queryKey: ["admin-buses"] });
    setEditing(null);
    selection.clear();
  };
  const create = useMutation({ mutationFn: adminApi.createBus, onSuccess: refresh });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: BusIn }) => adminApi.patchBus(id, body),
    onSuccess: refresh,
  });
  const deactivate = useMutation({
    mutationFn: async (ids: string[]) => {
      const byId = new Map((query.data ?? []).map((b) => [b.id, b]));
      for (const id of ids) {
        const bus = byId.get(id);
        if (!bus) continue;
        await adminApi.patchBus(id, {
          name: bus.name,
          registration_number: bus.registration_number,
          model: bus.model,
          seat_count: bus.seat_count,
          layout_type: bus.layout_type,
          active: false,
        });
      }
    },
    onSuccess: refresh,
  });

  return (
    <>
      <AdminHeader
        title="Avtobuslar"
        sub="Avtopark va salon sxemalari"
        action={
          <Button onClick={() => setEditing("new")} icon={<Plus size={16} weight="bold" />}>
            Avtobus qo‘shish
          </Button>
        }
      />
      {query.isError && <ErrorBox error={query.error} />}
      {deactivate.isError && <ErrorBox error={deactivate.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Nomi, model, raqam…"
        status={status}
        onStatus={setStatus}
        statusOptions={ACTIVE_FILTER}
        resultCount={rows.length}
        totalCount={query.data?.length}
      />

      <BulkBar
        selectedCount={selection.count}
        filteredCount={removable.length}
        pending={deactivate.isPending}
        onDeleteSelected={() => deactivate.mutate(selection.selectedIds)}
        onDeleteFiltered={() => deactivate.mutate(removable)}
      />

      {query.isLoading ? (
        <TableSkeleton cols={6} />
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
              <Th>Nomi</Th>
              <Th>Model</Th>
              <Th>Davlat raqami</Th>
              <Th className="text-right">Joylar</Th>
              <Th>Holat</Th>
              <Th className="text-right">Amallar</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <TableEmpty colSpan={7}>Hech narsa topilmadi.</TableEmpty>}
            {rows.map((bus) => (
              <Tr key={bus.id}>
                <Td>
                  {bus.active ? (
                    <RowCheckbox
                      checked={selection.isSelected(bus.id)}
                      onChange={() => selection.toggle(bus.id)}
                      label={`${bus.name} ni tanlash`}
                    />
                  ) : (
                    <span className="inline-block w-4" />
                  )}
                </Td>
                <Td className="font-medium">{bus.name}</Td>
                <Td className="text-muted">{bus.model}</Td>
                <Td className="tnum whitespace-nowrap">{bus.registration_number}</Td>
                <Td className="tnum text-right">{bus.seat_count}</Td>
                <Td>
                  <ActiveBadge active={bus.active} />
                </Td>
                <Td className="text-right">
                  <div className="flex justify-end gap-1.5">
                    <Link
                      to={`/admin/buses/${bus.id}/layout`}
                      className="inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-[10px] border border-line/80 bg-surface/60 px-2.5 text-[13px] font-medium text-ink no-underline transition-colors duration-200 hover:border-accent/50 hover:bg-accent-soft/70"
                    >
                      <Armchair size={14} weight="bold" />
                      Salon sxemasi
                    </Link>
                    <RowAction onClick={() => setEditing(bus)}>
                      <PencilSimple size={14} weight="bold" />
                      Tahrirlash
                    </RowAction>
                    {bus.active && (
                      <RowAction
                        tone="danger"
                        onClick={() => deactivate.mutate([bus.id])}
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
        title={editing === "new" ? "Yangi avtobus" : "Avtobusni tahrirlash"}
        sub={editing === "new" ? "Saqlagandan so‘ng salon sxemasini quring." : undefined}
        wide
      >
        {editing !== null && (
          <BusForm
            key={editing === "new" ? "new" : editing.id}
            initial={
              editing === "new"
                ? EMPTY
                : {
                    name: editing.name,
                    registration_number: editing.registration_number,
                    model: editing.model,
                    seat_count: editing.seat_count,
                    layout_type: editing.layout_type,
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
