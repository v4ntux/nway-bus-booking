import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../../api/admin";
import { FilterBar, matchesQuery } from "../../components/AdminFilters";
import { AdminHeader, PAYMENT_STATUS_UZ, StatusBadge, Table, TableEmpty, TableSkeleton, Td, Th, Tr } from "../../components/Table";
import { Amount, ErrorBox } from "../../components/Ui";
import { PAYMENT_METHOD_UZ, PAYMENT_PROVIDER_UZ, formatClock, formatDayLabel } from "../../utils/format";

export function PaymentsPage() {
  const query = useQuery({ queryKey: ["admin-payments"], queryFn: () => adminApi.payments() });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const items = useMemo(() => {
    return (query.data?.items ?? []).filter((p) => {
      if (status && p.status !== status) return false;
      return matchesQuery(
        [p.provider, p.method, p.status, PAYMENT_PROVIDER_UZ[p.provider], PAYMENT_METHOD_UZ[p.method]],
        search,
      );
    });
  }, [query.data, search, status]);

  const paid = items.filter((p) => p.status === "paid").reduce((sum, p) => sum + p.amount_minor, 0);
  const currency = items[0]?.currency ?? "UZS";

  return (
    <>
      <AdminHeader title="To‘lovlar" sub="Bronlar bo‘yicha o‘tkazmalar" />
      {query.isError && <ErrorBox error={query.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Provayder, usul…"
        status={status}
        onStatus={setStatus}
        statusOptions={Object.entries(PAYMENT_STATUS_UZ).map(([value, v]) => ({ value, label: v.label }))}
        resultCount={items.length}
        totalCount={query.data?.items.length}
      />

      {items.length > 0 && (
        <div className="glass flex flex-wrap items-center justify-between gap-3 rounded-panel px-4 py-3.5 sm:px-5">
          <span className="text-[14px] text-muted">Filtrdagi to‘langan summa</span>
          <Amount minor={paid} currency={currency} className="text-[20px] font-semibold text-ink" />
        </div>
      )}

      {query.isLoading ? (
        <TableSkeleton cols={5} />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Yaratilgan</Th>
              <Th>Usul</Th>
              <Th>Provayder</Th>
              <Th>Holat</Th>
              <Th>To‘langan</Th>
              <Th className="text-right">Summa</Th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <TableEmpty colSpan={6}>Hech narsa topilmadi.</TableEmpty>}
            {items.map((p) => (
              <Tr key={p.id}>
                <Td className="whitespace-nowrap">
                  <span className="tnum">{formatClock(p.created_at, "Asia/Tashkent")}</span>
                  <span className="ml-2 text-[13px] text-muted">{formatDayLabel(p.created_at, "Asia/Tashkent")}</span>
                </Td>
                <Td>{PAYMENT_METHOD_UZ[p.method] ?? p.method}</Td>
                <Td className="text-muted">{PAYMENT_PROVIDER_UZ[p.provider] ?? p.provider}</Td>
                <Td>
                  <StatusBadge status={p.status} kind="payment" />
                </Td>
                <Td className="tnum whitespace-nowrap text-muted">
                  {p.paid_at
                    ? `${formatClock(p.paid_at, "Asia/Tashkent")} ${formatDayLabel(p.paid_at, "Asia/Tashkent")}`
                    : "-"}
                </Td>
                <Td className="whitespace-nowrap text-right">
                  <Amount minor={p.amount_minor} currency={p.currency} className="font-medium" />
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}
