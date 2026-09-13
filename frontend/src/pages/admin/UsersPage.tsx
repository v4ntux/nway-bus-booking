import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../../api/admin";
import { FilterBar, matchesQuery } from "../../components/AdminFilters";
import { AdminHeader, Table, TableEmpty, TableSkeleton, Td, Th, Tr } from "../../components/Table";
import { Badge, ErrorBox } from "../../components/Ui";
import { formatDayLabel } from "../../utils/format";

const ROLE_UZ: Record<string, string> = {
  superadmin: "superadmin",
  admin: "kompaniya admini",
  operator: "operator",
  driver: "haydovchi",
  passenger: "yo‘lovchi",
};

export function UsersPage() {
  const query = useQuery({ queryKey: ["admin-users"], queryFn: () => adminApi.users() });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const items = useMemo(() => {
    return (query.data?.items ?? []).filter((u) => {
      if (status === "1" && u.status !== "active") return false;
      if (status === "0" && u.status === "active") return false;
      return matchesQuery([u.phone, u.email, u.first_name, u.last_name, u.role, ROLE_UZ[u.role]], search);
    });
  }, [query.data, search, status]);

  return (
    <>
      <AdminHeader title="Foydalanuvchilar" sub="Xodimlar va yo‘lovchi akkauntlari" />
      {query.isError && <ErrorBox error={query.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Telefon, email, ism, rol…"
        status={status}
        onStatus={setStatus}
        statusOptions={[
          { value: "1", label: "Faol" },
          { value: "0", label: "Bloklangan" },
        ]}
        resultCount={items.length}
        totalCount={query.data?.items.length}
      />

      {query.isLoading ? (
        <TableSkeleton cols={5} />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Telefon</Th>
              <Th>Ism</Th>
              <Th>Email</Th>
              <Th>Rol</Th>
              <Th>Ro‘yxatdan o‘tgan</Th>
              <Th className="text-right">Holat</Th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <TableEmpty colSpan={6}>Hech narsa topilmadi.</TableEmpty>}
            {items.map((u) => (
              <Tr key={u.id}>
                <Td className="tnum whitespace-nowrap font-medium">{u.phone}</Td>
                <Td>{[u.first_name, u.last_name].filter(Boolean).join(" ") || <span className="text-faint">-</span>}</Td>
                <Td className="text-muted">{u.email ?? "-"}</Td>
                <Td>
                  <Badge tone={u.role === "passenger" ? "neutral" : "sky"}>{ROLE_UZ[u.role] ?? u.role}</Badge>
                </Td>
                <Td className="whitespace-nowrap text-muted">{formatDayLabel(u.created_at, "Asia/Tashkent")}</Td>
                <Td className="text-right">
                  <Badge tone={u.status === "active" ? "positive" : "danger"}>
                    {u.status === "active" ? "faol" : "bloklangan"}
                  </Badge>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}
