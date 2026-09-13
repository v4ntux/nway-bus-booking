import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PencilSimple, Plus, Power } from "@phosphor-icons/react";
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
import type { City, CityIn } from "../../types/api";

const EMPTY: CityIn = { name: "", country: "UZ", timezone: "Asia/Tashkent", active: true };

function CityForm({
  initial,
  pending,
  error,
  onSubmit,
}: {
  initial: CityIn;
  pending: boolean;
  error: unknown;
  onSubmit: (body: CityIn) => void;
}) {
  const [form, setForm] = useState<CityIn>(initial);
  const set = <K extends keyof CityIn>(key: K, value: CityIn[K]) => setForm((f) => ({ ...f, [key]: value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ ...form, name: form.name.trim(), country: form.country.toUpperCase() });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {error != null && <ErrorBox error={error} />}
      <Field label="Nomi" htmlFor="city-name">
        <Input id="city-name" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Samarqand" required />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Davlat" hint="ISO kodi: UZ, KZ" htmlFor="city-country">
          <Input
            id="city-country"
            value={form.country}
            onChange={(e) => set("country", e.target.value.toUpperCase())}
            maxLength={2}
            className="tnum"
            required
          />
        </Field>
        <Field label="Vaqt mintaqasi" htmlFor="city-tz">
          <Input id="city-tz" value={form.timezone} onChange={(e) => set("timezone", e.target.value)} placeholder="Asia/Tashkent" required />
        </Field>
      </div>
      <label className="flex items-center gap-3 text-[14px] text-ink">
        <input type="checkbox" checked={form.active} onChange={(e) => set("active", e.target.checked)} className="h-4 w-4" />
        Faol (qidiruvda ko‘rinadi)
      </label>
      <Button type="submit" size="lg" block loading={pending}>
        Saqlash
      </Button>
    </form>
  );
}

export function CitiesPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["admin-cities"], queryFn: adminApi.cities });
  const [editing, setEditing] = useState<City | "new" | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const rows = useMemo(() => {
    const all = filterByActive(query.data ?? [], status);
    return all.filter((c) => matchesQuery([c.name, c.country, c.timezone], search));
  }, [query.data, search, status]);

  const removable = useMemo(() => rows.filter((c) => c.active).map((c) => c.id), [rows]);
  const selection = useRowSelection(removable);

  const refresh = () => {
    client.invalidateQueries({ queryKey: ["admin-cities"] });
    setEditing(null);
    selection.clear();
  };
  const create = useMutation({ mutationFn: adminApi.createCity, onSuccess: refresh });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: CityIn }) => adminApi.patchCity(id, body),
    onSuccess: refresh,
  });
  const deactivate = useMutation({
    mutationFn: async (ids: string[]) => {
      for (const id of ids) await adminApi.deactivateCity(id);
    },
    onSuccess: refresh,
  });

  return (
    <>
      <AdminHeader
        title="Shaharlar"
        sub="Jo‘nash va yetib borish nuqtalari"
        action={
          <Button onClick={() => setEditing("new")} icon={<Plus size={16} weight="bold" />}>
            Shahar qo‘shish
          </Button>
        }
      />

      {query.isError && <ErrorBox error={query.error} />}
      {deactivate.isError && <ErrorBox error={deactivate.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Nomi, davlat, vaqt mintaqasi…"
        status={status}
        onStatus={setStatus}
        statusOptions={ACTIVE_FILTER}
        statusLabel="Holat"
        resultCount={rows.length}
        totalCount={query.data?.length}
      />

      <BulkBar
        selectedCount={selection.count}
        filteredCount={removable.length}
        pending={deactivate.isPending}
        onDeleteSelected={() => deactivate.mutate(selection.selectedIds)}
        onDeleteFiltered={() => deactivate.mutate(removable)}
        deleteLabel="Tanlanganlarni o‘chirish"
        deleteAllLabel="Filtrdagilarni o‘chirish"
      />

      {query.isLoading ? (
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
              <Th>Nomi</Th>
              <Th>Davlat</Th>
              <Th>Vaqt mintaqasi</Th>
              <Th>Holat</Th>
              <Th className="text-right">Amallar</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <TableEmpty colSpan={6}>Hech narsa topilmadi.</TableEmpty>}
            {rows.map((c) => (
              <Tr key={c.id}>
                <Td>
                  {c.active ? (
                    <RowCheckbox
                      checked={selection.isSelected(c.id)}
                      onChange={() => selection.toggle(c.id)}
                      label={`${c.name} ni tanlash`}
                    />
                  ) : (
                    <span className="inline-block w-4" />
                  )}
                </Td>
                <Td className="font-medium">{c.name}</Td>
                <Td className="tnum">{c.country}</Td>
                <Td className="text-muted">{c.timezone}</Td>
                <Td>
                  <ActiveBadge active={c.active} />
                </Td>
                <Td className="text-right">
                  <div className="flex justify-end gap-1.5">
                    <RowAction onClick={() => setEditing(c)}>
                      <PencilSimple size={14} weight="bold" />
                      Tahrirlash
                    </RowAction>
                    {c.active && (
                      <RowAction
                        tone="danger"
                        onClick={() => deactivate.mutate([c.id])}
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
        title={editing === "new" ? "Yangi shahar" : "Shaharni tahrirlash"}
      >
        {editing !== null && (
          <CityForm
            key={editing === "new" ? "new" : editing.id}
            initial={
              editing === "new"
                ? EMPTY
                : { name: editing.name, country: editing.country, timezone: editing.timezone, active: editing.active }
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
