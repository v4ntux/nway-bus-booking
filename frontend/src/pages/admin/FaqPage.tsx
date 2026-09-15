import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PencilSimple, Plus, Trash } from "@phosphor-icons/react";
import { faqAdminApi } from "../../api/support";
import { ACTIVE_FILTER, FilterBar, filterByActive, matchesQuery } from "../../components/AdminFilters";
import { Dialog } from "../../components/Dialog";
import { ActiveBadge, AdminHeader, RowAction, Table, TableEmpty, TableSkeleton, Td, Th, Tr } from "../../components/Table";
import { Button, ErrorBox, Field, Input, Select, inputClass } from "../../components/Ui";
import type { FaqIn, FaqItem, FaqLang } from "../../types/api";

const CATEGORIES: Record<string, string> = {
  booking: "Bron",
  payment: "To‘lov",
  tickets: "Chiptalar",
  trip: "Safar",
  general: "Umumiy",
};

const LANG_LABEL: Record<FaqLang, string> = { uz: "O‘zbekcha", ru: "Русский" };

const EMPTY: FaqIn = { lang: "uz", category: "booking", question: "", answer: "", position: 0, active: true };

function FaqForm({
  initial,
  pending,
  error,
  onSubmit,
}: {
  initial: FaqIn;
  pending: boolean;
  error: unknown;
  onSubmit: (body: FaqIn) => void;
}) {
  const [form, setForm] = useState<FaqIn>(initial);
  const set = <K extends keyof FaqIn>(key: K, value: FaqIn[K]) => setForm((f) => ({ ...f, [key]: value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ ...form, question: form.question.trim(), answer: form.answer.trim() });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {error != null && <ErrorBox error={error} />}
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Til" htmlFor="faq-lang">
          <Select id="faq-lang" value={form.lang} onChange={(e) => set("lang", e.target.value as FaqLang)}>
            <option value="uz">O‘zbekcha</option>
            <option value="ru">Русский</option>
          </Select>
        </Field>
        <Field label="Bo‘lim" htmlFor="faq-category">
          <Select id="faq-category" value={form.category} onChange={(e) => set("category", e.target.value)}>
            {Object.entries(CATEGORIES).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Tartib" hint="Kichigi yuqorida" htmlFor="faq-position">
          <Input
            id="faq-position"
            type="number"
            value={form.position}
            onChange={(e) => set("position", Number(e.target.value) || 0)}
            className="tnum"
          />
        </Field>
      </div>
      <Field label="Savol" htmlFor="faq-question">
        <Input id="faq-question" value={form.question} onChange={(e) => set("question", e.target.value)} maxLength={200} required />
      </Field>
      <Field label="Javob" hint="Botda va ilovada oddiy matn sifatida ko‘rinadi" htmlFor="faq-answer">
        <textarea
          id="faq-answer"
          value={form.answer}
          onChange={(e) => set("answer", e.target.value)}
          maxLength={4000}
          rows={6}
          required
          className={`${inputClass} h-auto py-3 leading-relaxed`}
        />
      </Field>
      <label className="flex items-center gap-3 text-[14px] text-ink">
        <input type="checkbox" checked={form.active} onChange={(e) => set("active", e.target.checked)} className="h-4 w-4" />
        Faol (botda va ilovada ko‘rinadi)
      </label>
      <Button type="submit" size="lg" block loading={pending}>
        Saqlash
      </Button>
    </form>
  );
}

export function FaqPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["admin-faq"], queryFn: faqAdminApi.list });
  const [editing, setEditing] = useState<FaqItem | "new" | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const rows = useMemo(() => {
    const all = filterByActive(query.data ?? [], status);
    return all.filter((f) => matchesQuery([f.question, f.answer, f.lang], search));
  }, [query.data, search, status]);

  const refresh = () => {
    client.invalidateQueries({ queryKey: ["admin-faq"] });
    client.invalidateQueries({ queryKey: ["faq"] });
    setEditing(null);
  };
  const create = useMutation({ mutationFn: faqAdminApi.create, onSuccess: refresh });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: FaqIn }) => faqAdminApi.patch(id, body),
    onSuccess: refresh,
  });
  const remove = useMutation({ mutationFn: faqAdminApi.remove, onSuccess: refresh });

  return (
    <>
      <AdminHeader
        title="Savollar (FAQ)"
        sub="Botdagi «Savollar» menyusi va ilovadagi yordam markazi"
        action={
          <Button onClick={() => setEditing("new")} icon={<Plus size={16} weight="bold" />}>
            Savol qo‘shish
          </Button>
        }
      />

      {query.isError && <ErrorBox error={query.error} />}
      {remove.isError && <ErrorBox error={remove.error} />}

      <FilterBar
        search={search}
        onSearch={setSearch}
        placeholder="Savol, javob, til…"
        status={status}
        onStatus={setStatus}
        statusOptions={ACTIVE_FILTER}
        statusLabel="Holat"
        resultCount={rows.length}
        totalCount={query.data?.length}
      />

      {query.isLoading ? (
        <TableSkeleton cols={5} />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Savol</Th>
              <Th>Til</Th>
              <Th>Bo‘lim</Th>
              <Th>Holat</Th>
              <Th className="text-right">Amallar</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <TableEmpty colSpan={5}>Hech narsa topilmadi.</TableEmpty>}
            {rows.map((f) => (
              <Tr key={f.id}>
                <Td className="max-w-[420px]">
                  <p className="truncate font-medium">{f.question}</p>
                  <p className="truncate text-[13px] text-muted">{f.answer}</p>
                </Td>
                <Td>{LANG_LABEL[f.lang]}</Td>
                <Td className="text-muted">{CATEGORIES[f.category] ?? f.category}</Td>
                <Td>
                  <ActiveBadge active={f.active} />
                </Td>
                <Td className="text-right">
                  <div className="flex justify-end gap-1.5">
                    <RowAction onClick={() => setEditing(f)}>
                      <PencilSimple size={14} weight="bold" />
                      Tahrirlash
                    </RowAction>
                    <RowAction
                      tone="danger"
                      disabled={remove.isPending}
                      onClick={() => {
                        if (window.confirm(`«${f.question}» savolini o‘chirasizmi?`)) remove.mutate(f.id);
                      }}
                    >
                      <Trash size={14} weight="bold" />
                      O‘chirish
                    </RowAction>
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
        title={editing === "new" ? "Yangi savol" : "Savolni tahrirlash"}
        wide
      >
        {editing !== null && (
          <FaqForm
            key={editing === "new" ? "new" : editing.id}
            initial={
              editing === "new"
                ? EMPTY
                : {
                    lang: editing.lang,
                    category: editing.category,
                    question: editing.question,
                    answer: editing.answer,
                    position: editing.position,
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
