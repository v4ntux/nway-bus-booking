import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "@phosphor-icons/react";
import { adminApi } from "../../api/admin";
import { ACTIVE_FILTER, FilterBar, filterByActive, matchesQuery } from "../../components/AdminFilters";
import { Dialog } from "../../components/Dialog";
import { ActiveBadge, AdminHeader, Table, TableEmpty, TableSkeleton, Td, Th, Tr } from "../../components/Table";
import { Button, ErrorBox, Field, Input } from "../../components/Ui";
import { formatPhoneDisplay, phoneToApi } from "../../utils/format";

export function CompaniesPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["admin-companies"], queryFn: adminApi.companies });
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const create = useMutation({
    mutationFn: () => adminApi.createCompany({ name: name.trim(), phone: phoneToApi(phone), active: true }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["admin-companies"] });
      setOpen(false);
      setName("");
      setPhone("");
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  const items = useMemo(() => {
    const all = filterByActive(query.data?.items ?? [], status);
    return all.filter((c) => matchesQuery([c.name, c.phone], search));
  }, [query.data, search, status]);

  return (
    <>
      <AdminHeader
        title="Kompaniyalar"
        sub="Tashuvchilar. Yangi kompaniyani faqat superadmin qo‘shadi."
        action={
          <Button onClick={() => setOpen(true)} icon={<Plus size={16} weight="bold" />}>
            Kompaniya qo‘shish
          </Button>
        }
      />
      {query.isError && <ErrorBox error={query.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Nomi yoki telefon…"
        status={status}
        onStatus={setStatus}
        statusOptions={ACTIVE_FILTER}
        resultCount={items.length}
        totalCount={query.data?.items.length}
      />

      {query.isLoading ? (
        <TableSkeleton cols={3} />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Nomi</Th>
              <Th>Telefon</Th>
              <Th className="text-right">Holat</Th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <TableEmpty colSpan={3}>Hech narsa topilmadi.</TableEmpty>}
            {items.map((c) => (
              <Tr key={c.id}>
                <Td className="font-medium">{c.name}</Td>
                <Td className="tnum whitespace-nowrap text-muted">{c.phone}</Td>
                <Td className="text-right">
                  <ActiveBadge active={c.active} />
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} title="Yangi kompaniya">
        <form onSubmit={submit} className="flex flex-col gap-4">
          {create.isError && <ErrorBox error={create.error} />}
          <Field label="Nomi" htmlFor="co-name">
            <Input id="co-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Registon Trans" required />
          </Field>
          <Field label="Telefon" htmlFor="co-phone">
            <Input
              id="co-phone"
              value={phone}
              onChange={(e) => setPhone(formatPhoneDisplay(e.target.value))}
              placeholder="+998 71 200 00 00"
              inputMode="tel"
              className="tnum"
              required
            />
          </Field>
          <Button type="submit" size="lg" block loading={create.isPending}>
            Saqlash
          </Button>
        </form>
      </Dialog>
    </>
  );
}
