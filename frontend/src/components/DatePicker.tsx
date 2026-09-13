import { useMemo, useState } from "react";
import { CaretLeft, CaretRight } from "@phosphor-icons/react";
import { formatMonthTitle, toDateInput } from "../utils/format";

const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

/** Monday-first, as calendars are printed in Uzbekistan. */
function leadingBlanks(first: Date) {
  return (first.getDay() + 6) % 7;
}

function sameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  );
}

export function DatePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (date: string) => void;
}) {
  const selected = useMemo(() => {
    const [y, m, d] = value.split("-").map(Number);
    return new Date(y, (m || 1) - 1, d || 1);
  }, [value]);

  const [cursor, setCursor] = useState(() => startOfMonth(selected));

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const first = startOfMonth(cursor);
  const daysInMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
  const blanks = leadingBlanks(first);
  const monthLabel = formatMonthTitle(cursor);

  // Nothing before today: a bus that has left cannot be booked.
  const atFirstMonth =
    cursor.getFullYear() === today.getFullYear() && cursor.getMonth() === today.getMonth();

  function shift(months: number) {
    setCursor((c) => new Date(c.getFullYear(), c.getMonth() + months, 1));
  }

  return (
    <div className="glass popover-in rounded-panel p-3 sm:p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => shift(-1)}
          disabled={atFirstMonth}
          aria-label="Oldingi oy"
          className="well inline-flex h-9 w-9 items-center justify-center rounded-[11px] text-muted transition-all duration-200 ease-out hover:border-accent/40 hover:text-ink disabled:opacity-35"
        >
          <CaretLeft size={16} weight="bold" />
        </button>
        <span className="text-[15px] font-semibold capitalize text-ink">{monthLabel}</span>
        <button
          type="button"
          onClick={() => shift(1)}
          aria-label="Keyingi oy"
          className="well inline-flex h-9 w-9 items-center justify-center rounded-[11px] text-muted transition-all duration-200 ease-out hover:border-accent/40 hover:text-ink"
        >
          <CaretRight size={16} weight="bold" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1" role="grid" aria-label="Kalendar">
        {WEEKDAYS.map((w) => (
          <span key={w} className="pb-1 text-center text-[12px] font-medium text-faint">
            {w}
          </span>
        ))}

        {Array.from({ length: blanks }).map((_, i) => (
          <span key={`b${i}`} aria-hidden="true" />
        ))}

        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = new Date(cursor.getFullYear(), cursor.getMonth(), i + 1);
          const iso = toDateInput(day);
          const past = day < today;
          const isSelected = sameDay(day, selected);
          const isToday = sameDay(day, today);

          return (
            <button
              key={iso}
              type="button"
              disabled={past}
              onClick={() => onChange(iso)}
              aria-pressed={isSelected}
              className={`tnum flex h-10 items-center justify-center rounded-[11px] text-[14px] transition-all duration-200 ease-out disabled:cursor-not-allowed disabled:opacity-30 ${
                isSelected
                  ? "btn-sun animate-pop-in font-semibold"
                  : isToday
                    ? "border border-accent/60 font-semibold text-ink hover:bg-accent-soft"
                    : "text-ink hover:bg-surface/70"
              }`}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
    </div>
  );
}
