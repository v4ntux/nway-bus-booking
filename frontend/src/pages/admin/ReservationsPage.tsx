import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CaretDown } from "@phosphor-icons/react";
import { adminApi } from "../../api/admin";
import {
  BulkBar,
  FilterBar,
  RowCheckbox,
  SelectAllCheckbox,
  useRowSelection,
} from "../../components/AdminFilters";
import {
  AdminHeader,
  RESERVATION_STATUS_UZ,
  RowAction,
  StatusBadge,
  Table,
  TableEmpty,
  TableSkeleton,
  Td,
  Th,
  Tr,
} from "../../components/Table";
import { Amount, ErrorBox } from "../../components/Ui";
import { PAYMENT_PROVIDER_UZ, formatDateTimeLong } from "../../utils/format";
import type { Reservation } from "../../types/api";

const ACTIONS: Record<string, string[]> = {
  pending: ["confirm", "mark-paid", "require-deposit", "reject", "cancel"],
  awaiting_admin_approval: ["confirm", "mark-paid", "require-deposit", "reject", "cancel"],
  awaiting_deposit: ["mark-deposit-received", "reject", "cancel"],
  confirmed: ["mark-no-show", "cancel"],
};

const ACTION_UZ: Record<string, string> = {
  confirm: "Tasdiqlash",
  cancel: "Bekor qilish",
  "require-deposit": "Oldindan to‘lov so‘rash",
  reject: "Rad etish",
  "mark-paid": "To‘langan deb belgilash",
  "mark-deposit-received": "Oldindan to‘lov olindi",
  "mark-no-show": "Kelmadi",
};

const DESTRUCTIVE = new Set(["cancel", "reject", "mark-no-show"]);

function Details({ r }: { r: Reservation }) {
  const seatByPassenger = new Map(r.seats.map((s) => [s.seat_id, s.seat_number]));
  const payment = r.payments.find((p) => p.status === "paid") ?? r.payments[0];
  return (
    <div className="grid gap-4 px-4 py-4 sm:grid-cols-2 sm:px-5">
      <div>
        <p className="mb-1.5 text-[12px] font-semibold text-muted">Yo‘lovchilar</p>
        <ul className="flex flex-col gap-1">
          {r.passengers.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 text-[14px]">
              <span className="text-ink">{[p.first_name, p.last_name].filter(Boolean).join(" ")}</span>
              <span className="tnum text-muted">{seatByPassenger.get(p.seat_id) ?? "-"}-joy</span>
            </li>
          ))}
        </ul>
      </div>
      <dl className="flex flex-col gap-1 text-[14px]">
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Yaratilgan</dt>
          <dd className="tnum text-ink">{formatDateTimeLong(r.created_at, "Asia/Tashkent")}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">To‘lov</dt>
          <dd className="text-ink">
            {payment ? PAYMENT_PROVIDER_UZ[payment.provider] ?? payment.provider : "-"}
            {payment?.paid_at && (
              <span className="tnum ml-2 text-muted">{formatDateTimeLong(payment.paid_at, "Asia/Tashkent")}</span>
            )}
          </dd>
        </div>
        {r.expires_at && r.status === "pending" && (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Bron muddati</dt>
            <dd className="tnum text-ink">{formatDateTimeLong(r.expires_at, "Asia/Tashkent")}</dd>
          </div>
        )}
        {r.deposit_required && (
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Oldindan to‘lov</dt>
            <dd className="text-ink">{r.deposit_received ? "olindi" : "kutilmoqda"}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

export function ReservationsPage() {
  const client = useQueryClient();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const params = new URLSearchParams({ page_size: "100" });
  if (status) params.set("status", status);

  const query = useQuery({
    queryKey: ["admin-reservations", status],
    queryFn: () => adminApi.reservations(params),
  });

  const items: Reservation[] = useMemo(() => {
    const all = query.data?.items ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return all;
    return all.filter(
      (r) =>
        r.public_code.toLowerCase().includes(q) ||
        r.contact_phone.includes(q) ||
        r.passengers.some((p) => `${p.first_name} ${p.last_name ?? ""}`.toLowerCase().includes(q)),
    );
  }, [query.data, search]);

  const cancellable = useMemo(
    () =>
      items
        .filter((r) => (ACTIONS[r.status] ?? []).includes("cancel"))
        .map((r) => r.id),
    [items],
  );
  const selection = useRowSelection(cancellable);

  const mutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => adminApi.reservationAction(id, action),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["admin-reservations"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      selection.clear();
    },
  });

  const bulkCancel = useMutation({
    mutationFn: async (ids: string[]) => {
      for (const id of ids) await adminApi.reservationAction(id, "cancel");
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["admin-reservations"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      selection.clear();
    },
  });

  return (
    <>
      <AdminHeader title="Bronlar" sub="Tasdiqlash, bekor qilish va to‘lovni belgilash" />

      {query.isError && <ErrorBox error={query.error} />}
      {(mutation.isError || bulkCancel.isError) && <ErrorBox error={mutation.error ?? bulkCancel.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Kod, telefon, ism…"
        status={status}
        onStatus={setStatus}
        statusOptions={Object.entries(RESERVATION_STATUS_UZ).map(([value, v]) => ({ value, label: v.label }))}
        resultCount={items.length}
        totalCount={query.data?.total}
      />

      <BulkBar
        selectedCount={selection.count}
        filteredCount={cancellable.length}
        pending={bulkCancel.isPending}
        onDeleteSelected={() => bulkCancel.mutate(selection.selectedIds)}
        onDeleteFiltered={() => bulkCancel.mutate(cancellable)}
        deleteLabel="Tanlanganlarni bekor qilish"
        deleteAllLabel="Filtrdagilarni bekor qilish"
      />

      {query.isLoading ? (
        <TableSkeleton cols={8} />
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
              <Th className="w-8" />
              <Th>Kod</Th>
              <Th>Holat</Th>
              <Th>Telefon</Th>
              <Th className="text-right">Joylar</Th>
              <Th className="text-right">Summa</Th>
              <Th>To‘lov</Th>
              <Th className="text-right">Amallar</Th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <TableEmpty colSpan={9}>Bu filtr bo‘yicha bronlar yo‘q.</TableEmpty>}
            {items.map((r) => {
              const expanded = open === r.id;
              const canCancel = (ACTIONS[r.status] ?? []).includes("cancel");
              return (
                <Fragment key={r.id}>
                  <Tr>
                    <Td>
                      {canCancel ? (
                        <RowCheckbox
                          checked={selection.isSelected(r.id)}
                          onChange={() => selection.toggle(r.id)}
                          label={`${r.public_code} ni tanlash`}
                        />
                      ) : (
                        <span className="inline-block w-4" />
                      )}
                    </Td>
                    <Td className="pr-0">
                      <button
                        type="button"
                        onClick={() => setOpen(expanded ? null : r.id)}
                        aria-expanded={expanded}
                        aria-label="Tafsilotlar"
                        className="inline-flex h-7 w-7 items-center justify-center rounded-[8px] text-muted hover:bg-surface/60 hover:text-ink"
                      >
                        <CaretDown
                          size={14}
                          weight="bold"
                          className={`transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}
                        />
                      </button>
                    </Td>
                    <Td className="tnum font-medium tracking-wide">{r.public_code}</Td>
                    <Td>
                      <StatusBadge status={r.status} />
                    </Td>
                    <Td className="tnum whitespace-nowrap">{r.contact_phone}</Td>
                    <Td className="tnum text-right">
                      {r.seats.map((s) => s.seat_number).filter(Boolean).join(", ") || r.seats.length}
                    </Td>
                    <Td className="whitespace-nowrap text-right">
                      <Amount minor={r.total_amount_minor} currency={r.currency} className="font-medium" />
                    </Td>
                    <Td>
                      <StatusBadge status={r.payment_status} kind="payment" />
                    </Td>
                    <Td>
                      <div className="flex flex-wrap justify-end gap-1.5">
                        {(ACTIONS[r.status] ?? []).map((action) => (
                          <RowAction
                            key={action}
                            tone={DESTRUCTIVE.has(action) ? "danger" : "default"}
                            disabled={mutation.isPending}
                            onClick={() => mutation.mutate({ id: r.id, action })}
                          >
                            {ACTION_UZ[action]}
                          </RowAction>
                        ))}
                      </div>
                    </Td>
                  </Tr>
                  {expanded && (
                    <tr className="bg-surface/30">
                      <td colSpan={9} className="border-b border-hairline/80 p-0">
                        <Details r={r} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </Table>
      )}
    </>
  );
}
