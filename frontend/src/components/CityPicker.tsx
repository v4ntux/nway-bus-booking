import { useEffect, useId, useMemo, useRef, useState } from "react";
import { CaretDown, Check, MagnifyingGlass } from "@phosphor-icons/react";
import type { City } from "../types/api";

/**
 * A searchable city list. A native <select> stops working the moment an
 * operator adds fifty cities, and it cannot carry the origin / destination
 * colour that ties the field to the route line elsewhere in the flow.
 */
export function CityPicker({
  label,
  cities,
  value,
  onChange,
  exclude,
  placeholder = "Shaharni tanlang",
  loading = false,
  tone = "neutral",
}: {
  label: string;
  cities: City[];
  value: string;
  onChange: (id: string) => void;
  exclude?: string;
  placeholder?: string;
  loading?: boolean;
  tone?: "neutral" | "origin" | "destination";
}) {
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState("");
  const [cursor, setCursor] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  const options = useMemo(() => {
    const q = term.trim().toLowerCase();
    return cities
      .filter((c) => c.id !== exclude)
      .filter((c) => !q || c.name.toLowerCase().includes(q));
  }, [cities, exclude, term]);

  const selected = cities.find((c) => c.id === value) ?? null;

  useEffect(() => {
    if (!open) return;
    searchRef.current?.focus();
    setCursor(0);
    function onDocPointer(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onDocPointer);
    return () => document.removeEventListener("pointerdown", onDocPointer);
  }, [open]);

  function commit(id: string) {
    onChange(id);
    setOpen(false);
    setTerm("");
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      const delta = event.key === "ArrowDown" ? 1 : -1;
      setCursor((c) => Math.min(options.length - 1, Math.max(0, c + delta)));
      return;
    }
    if (event.key === "Enter" && open && options[cursor]) {
      event.preventDefault();
      commit(options[cursor].id);
    }
  }

  const dot =
    tone === "origin"
      ? "bg-accent shadow-[0_0_10px_rgb(var(--c-accent)/0.7)]"
      : tone === "destination"
        ? "bg-sky shadow-[0_0_10px_rgb(var(--c-sky)/0.7)]"
        : "bg-line";

  return (
    <div ref={rootRef} className="relative" onKeyDown={onKeyDown}>
      <span className="mb-2 block text-sm font-medium text-ink">{label}</span>
      <button
        type="button"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-haspopup="listbox"
        disabled={loading}
        onClick={() => setOpen((o) => !o)}
        className={`well flex h-14 w-full items-center gap-3 rounded-control pl-3 pr-3.5 text-left transition-all duration-200 ease-out hover:border-accent/40 hover:bg-surface disabled:opacity-50 ${
          open ? "border-accent bg-surface shadow-[0_0_0_4px_rgb(var(--c-accent)/0.18)]" : ""
        }`}
      >
        <span aria-hidden="true" className={`h-2.5 w-2.5 shrink-0 rounded-full ${dot}`} />
        <span className={`min-w-0 flex-1 truncate text-[16px] ${selected ? "font-semibold text-ink" : "text-faint"}`}>
          {loading ? "Yuklanmoqda…" : (selected?.name ?? placeholder)}
        </span>
        <CaretDown
          size={16}
          weight="bold"
          aria-hidden="true"
          className={`shrink-0 text-muted transition-transform duration-300 ease-out ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="glass-strong popover-in absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-panel shadow-lift">
          <div className="flex items-center gap-2 border-b border-hairline/80 px-3">
            <MagnifyingGlass size={16} weight="bold" className="shrink-0 text-faint" />
            <input
              ref={searchRef}
              value={term}
              onChange={(e) => {
                setTerm(e.target.value);
                setCursor(0);
              }}
              placeholder="Shahar qidirish"
              aria-label="Shahar qidirish"
              className="h-11 w-full bg-transparent text-[15px] text-ink outline-none"
            />
          </div>
          <ul id={listId} role="listbox" className="max-h-64 overflow-y-auto py-1">
            {options.length === 0 && (
              <li className="px-3.5 py-3 text-[14px] text-muted">Hech narsa topilmadi</li>
            )}
            {options.map((city, i) => {
              const isSelected = city.id === value;
              return (
                <li key={city.id} role="option" aria-selected={isSelected}>
                  <button
                    type="button"
                    onMouseEnter={() => setCursor(i)}
                    onClick={() => commit(city.id)}
                    className={`flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left transition-colors duration-150 ${
                      i === cursor ? "bg-accent-soft/70" : "hover:bg-surface/60"
                    }`}
                  >
                    <span className="truncate text-[15px] font-medium text-ink">{city.name}</span>
                    {isSelected && <Check size={15} weight="bold" className="shrink-0 text-accent-strong" />}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
