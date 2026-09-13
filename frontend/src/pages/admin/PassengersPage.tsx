import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../../api/admin";
import { FilterBar, matchesQuery } from "../../components/AdminFilters";
import { AdminHeader, Table, TableEmpty, TableSkeleton, Td, Th, Tr } from "../../components/Table";
import { ErrorBox } from "../../components/Ui";

export function PassengersPage() {
  const query = useQuery({ queryKey: ["admin-passengers"], queryFn: () => adminApi.passengers() });
  const [search, setSearch] = useState("");

  const items = useMemo(() => {
    return (query.data?.items ?? []).filter((p) =>
      matchesQuery([p.first_name, p.last_name, p.phone], search),
    );
  }, [query.data, search]);

  return (
    <>
      <AdminHeader title="Yo‘lovchilar" sub="Rasmiylashtirilgan bronlar bo‘yicha kim yo‘lga chiqadi" />
      {query.isError && <ErrorBox error={query.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Ism yoki telefon…"
        resultCount={items.length}
        totalCount={query.data?.items.length}
      />

      {query.isLoading ? (
        <TableSkeleton cols={2} />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Ism</Th>
              <Th>Telefon</Th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <TableEmpty colSpan={2}>Yo‘lovchilar topilmadi.</TableEmpty>}
            {items.map((p) => (
              <Tr key={p.id}>
                <Td className="font-medium">{[p.first_name, p.last_name].filter(Boolean).join(" ")}</Td>
                <Td className="tnum whitespace-nowrap text-muted">{p.phone ?? "-"}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}
