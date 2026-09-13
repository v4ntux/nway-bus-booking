import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { MagnifyingGlass, Trash, X } from "@phosphor-icons/react";
import { Button, Input, Select } from "./Ui";

/** Instant client-side search across string fields. */
export function matchesQuery(haystack: Array<string | number | null | undefined>, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return haystack.some((part) => String(part ?? "").toLowerCase().includes(q));
}

export function useRowSelection(ids: string[]) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const idKey = ids.join("|");

  // Drop selections that left the current filtered page.
  useEffect(() => {
    setSelected((prev) => {
      const next = new Set([...prev].filter((id) => ids.includes(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [idKey, ids]);

  const allSelected = ids.length > 0 && ids.every((id) => selected.has(id));
  const someSelected = ids.some((id) => selected.has(id));

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelected((prev) => {
      if (ids.length > 0 && ids.every((id) => prev.has(id))) return new Set();
      return new Set(ids);
    });
  }, [ids]);

  const clear = useCallback(() => setSelected(new Set()), []);

  return {
    selected,
    selectedIds: [...selected],
    count: selected.size,
    allSelected,
    someSelected,
    toggle,
    toggleAll,
    clear,
    isSelected: (id: string) => selected.has(id),
  };
}

type FilterOption = { value: string; label: string };

type FilterBarProps = {
  search: string;
  onSearch: (value: string) => void;
  placeholder?: string;
  /** Optional status / active chip select. */
  status?: string;
  onStatus?: (value: string) => void;
  statusOptions?: FilterOption[];
  statusLabel?: string;
  children?: ReactNode;
  resultCount?: number;
  totalCount?: number;
};

export function FilterBar({
  search,
  onSearch,
  placeholder = "Qidirish…",
  status,
  onStatus,
  statusOptions,
  statusLabel = "Holat",
  children,
  resultCount,
  totalCount,
}: FilterBarProps) {
  const hasFilter = Boolean(search.trim()) || Boolean(status);
  return (
    <div className="glass flex flex-col gap-3 rounded-panel p-3 sm:flex-row sm:flex-wrap sm:items-center sm:p-3.5">
      <label className="relative min-w-0 flex-1 sm:max-w-xs">
        <span className="sr-only">Qidirish</span>
        <MagnifyingGlass
          size={16}
          weight="bold"
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
          aria-hidden="true"
        />
        <Input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder={placeholder}
          className="!pl-9"
        />
      </label>
      {statusOptions && onStatus && (
        <Select
          aria-label={statusLabel}
          value={status ?? ""}
          onChange={(e) => onStatus(e.target.value)}
          className="sm:w-44"
        >
          <option value="">Barchasi</option>
          {statusOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      )}
      {children}
      <div className="ml-auto flex items-center gap-2">
        {typeof resultCount === "number" && (
          <span className="tnum text-[13px] text-muted">
            {resultCount}
            {typeof totalCount === "number" && totalCount !== resultCount ? ` / ${totalCount}` : ""} ta
          </span>
        )}
        {hasFilter && (
          <button
            type="button"
            onClick={() => {
              onSearch("");
              onStatus?.("");
            }}
            className="inline-flex h-9 items-center gap-1.5 rounded-[10px] px-2.5 text-[13px] font-medium text-muted hover:bg-surface/60 hover:text-ink"
          >
            <X size={14} weight="bold" />
            Tozalash
          </button>
        )}
      </div>
    </div>
  );
}

type BulkBarProps = {
  selectedCount: number;
  filteredCount: number;
  pending?: boolean;
  /** Soft-delete / deactivate selected rows. */
  onDeleteSelected?: () => void;
  /** Soft-delete every row matching the current filter. */
  onDeleteFiltered?: () => void;
  deleteLabel?: string;
  deleteAllLabel?: string;
  extra?: ReactNode;
};

export function BulkBar({
  selectedCount,
  filteredCount,
  pending,
  onDeleteSelected,
  onDeleteFiltered,
  deleteLabel = "Tanlanganlarni o‘chirish",
  deleteAllLabel = "Filtrdagilarni o‘chirish",
  extra,
}: BulkBarProps) {
  if (selectedCount === 0 && filteredCount === 0) return null;
  if (selectedCount === 0 && !onDeleteFiltered) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-panel border border-accent/35 bg-accent-soft/80 px-3 py-2.5 backdrop-blur-md">
      <p className="mr-auto text-[13.5px] font-medium text-accent-strong">
        {selectedCount > 0 ? (
          <>
            <span className="tnum">{selectedCount}</span> ta tanlangan
          </>
        ) : (
          <>
            Filtrda <span className="tnum">{filteredCount}</span> ta
          </>
        )}
      </p>
      {extra}
      {selectedCount > 0 && onDeleteSelected && (
        <Button
          variant="danger"
          size="sm"
          loading={pending}
          onClick={() => {
            if (window.confirm(`${selectedCount} ta yozuv o‘chirilsinmi?`)) onDeleteSelected();
          }}
          icon={<Trash size={14} weight="bold" />}
        >
          {deleteLabel}
        </Button>
      )}
      {onDeleteFiltered && filteredCount > 0 && (
        <Button
          variant={selectedCount > 0 ? "ghost" : "danger"}
          size="sm"
          loading={pending}
          onClick={() => {
            if (
              window.confirm(
                `Filtrdagi ${filteredCount} ta yozuvning hammasi o‘chirilsinmi? Bu amalni qaytarib bo‘lmaydi.`,
              )
            ) {
              onDeleteFiltered();
            }
          }}
          icon={<Trash size={14} weight="bold" />}
        >
          {deleteAllLabel}
        </Button>
      )}
    </div>
  );
}

export function SelectAllCheckbox({
  allSelected,
  someSelected,
  onToggle,
  disabled,
}: {
  allSelected: boolean;
  someSelected: boolean;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <input
      type="checkbox"
      checked={allSelected}
      ref={(el) => {
        if (el) el.indeterminate = !allSelected && someSelected;
      }}
      onChange={onToggle}
      disabled={disabled}
      aria-label="Hammasini tanlash"
      className="h-4 w-4 accent-[rgb(var(--c-accent))]"
    />
  );
}

export function RowCheckbox({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      aria-label={label}
      className="h-4 w-4 accent-[rgb(var(--c-accent))]"
    />
  );
}

/** Active filter options shared by cities / routes / buses. */
export const ACTIVE_FILTER: FilterOption[] = [
  { value: "1", label: "Faol" },
  { value: "0", label: "O‘chirilgan" },
];

export function filterByActive<T extends { active: boolean }>(rows: T[], status: string): T[] {
  if (status === "1") return rows.filter((r) => r.active);
  if (status === "0") return rows.filter((r) => !r.active);
  return rows;
}

export function useDeferredSearch(initial = "") {
  const [search, setSearch] = useState(initial);
  const deferred = useMemo(() => search, [search]);
  return { search, setSearch, query: deferred };
}
