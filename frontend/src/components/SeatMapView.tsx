import { useMemo } from "react";
import type { CSSProperties, KeyboardEvent, ReactElement } from "react";
import { DoorOpen, GenderFemale, SteeringWheel } from "@phosphor-icons/react";
import type { SeatCell, SeatMap } from "../types/api";

const STATUS_UZ: Record<string, string> = {
  available: "bo‘sh",
  selected: "tanlangan",
  reserved: "band",
  blocked: "mavjud emas",
};

/** Panes are two rows tall, so glazing is grouped in pairs from the front. */
const ROWS_PER_PANE = 2;

type Props = {
  map: SeatMap;
  selected: string[];
  onToggle: (seatId: string) => void;
};

/*
 * The coach is drawn from above, driver at the top, kerb-side (right) doors.
 * Column widths come from the layout itself: a column that is an aisle in
 * most rows is drawn narrow, so the cabin reads 2 + aisle + 2 and the rear
 * bench spans the full width like it does in a real bus.
 */
export function SeatMapView({ map, selected, onToggle }: Props) {
  const grid = useMemo(() => {
    const rows: SeatCell[][] = Array.from({ length: map.rows }, () =>
      Array.from({ length: map.columns }, () => ({
        row: 0,
        column: 0,
        cell_type: "empty",
        seat: null,
      })),
    );
    for (const cell of map.cells) {
      if (cell.row < map.rows && cell.column < map.columns) {
        rows[cell.row][cell.column] = cell;
      }
    }
    return rows;
  }, [map]);

  const hasWomenRows = map.cells.some((c) => c.seat?.is_women_only);

  const { aisleCols, fullRows, doorRows } = useMemo(() => {
    const aisleCount = new Array<number>(map.columns).fill(0);
    const full = new Set<number>();
    const doorsLeft = new Set<number>();
    const doorsRight = new Set<number>();
    const mid = (map.columns - 1) / 2;

    grid.forEach((row, r) => {
      if (row.every((c) => c.seat)) full.add(r);
      row.forEach((c, i) => {
        if (c.cell_type === "aisle" || (!c.seat && c.cell_type !== "door")) aisleCount[i] += 1;
        if (c.cell_type === "door") (i > mid ? doorsRight : doorsLeft).add(r);
      });
    });

    const aisles = new Set<number>();
    aisleCount.forEach((n, i) => {
      if (n >= (map.rows - full.size) * 0.8) aisles.add(i);
    });
    return { aisleCols: aisles, fullRows: full, doorRows: { left: doorsLeft, right: doorsRight } };
  }, [grid, map.columns, map.rows]);

  const columnTemplate = [
    "var(--pane)",
    ...Array.from({ length: map.columns }, (_, i) => (aisleCols.has(i) ? "var(--aisle)" : "var(--seat)")),
    "var(--pane)",
  ].join(" ");

  function onKey(event: KeyboardEvent<HTMLButtonElement>, row: number, col: number) {
    const deltas: Record<string, [number, number]> = {
      ArrowUp: [-1, 0],
      ArrowDown: [1, 0],
      ArrowLeft: [0, -1],
      ArrowRight: [0, 1],
    };
    const delta = deltas[event.key];
    if (!delta) return;
    event.preventDefault();
    let r = row;
    let c = col;
    for (let step = 0; step < map.rows * map.columns; step += 1) {
      r += delta[0];
      c += delta[1];
      if (r < 0 || r >= map.rows || c < 0 || c >= map.columns) return;
      const target = grid[r][c];
      if (target.seat) {
        document.getElementById(`seat-${target.seat.id}`)?.focus();
        return;
      }
    }
  }

  function renderSeat(cell: SeatCell, rIdx: number, cIdx: number, style?: CSSProperties) {
    const seat = cell.seat!;
    const isSelected = selected.includes(seat.id);
    const status = isSelected ? "selected" : seat.status;
    const clickable = seat.status === "available" || isSelected;
    const women = Boolean(seat.is_women_only);

    const tone =
      status === "selected"
        ? "seat-picked"
        : status === "available"
          ? women
            ? "seat-women"
            : ""
          : "seat-taken";

    return (
      <button
        key={`s-${rIdx}-${cIdx}`}
        id={`seat-${seat.id}`}
        type="button"
        role="gridcell"
        disabled={!clickable}
        onClick={() => clickable && onToggle(seat.id)}
        onKeyDown={(e) => onKey(e, rIdx, cIdx)}
        aria-label={`Joy ${seat.seat_number}, ${STATUS_UZ[status]}${women ? ", faqat ayollar uchun" : ""}`}
        aria-pressed={isSelected}
        style={style}
        className={`seat tnum text-[15px] font-semibold ${tone} ${status === "reserved" || status === "blocked" ? "line-through" : ""}`}
      >
        {seat.seat_number}
        {women && status !== "reserved" && status !== "blocked" && (
          <GenderFemale
            aria-hidden="true"
            size={11}
            weight="bold"
            className={`absolute right-1.5 top-1.5 ${status === "selected" ? "opacity-70" : "opacity-80"}`}
          />
        )}
      </button>
    );
  }

  const items: ReactElement[] = [];

  // Aisle lanes and glazing first so seats paint over them if anything overlaps.
  const lastNormalRow = Math.max(0, ...Array.from({ length: map.rows }, (_, r) => r).filter((r) => !fullRows.has(r)));
  aisleCols.forEach((col) => {
    items.push(
      <span
        key={`aisle-${col}`}
        aria-hidden="true"
        className="aisle-lane"
        style={{ gridColumn: col + 2, gridRow: `1 / span ${lastNormalRow + 1}` }}
      />,
    );
  });

  for (let start = 0; start < map.rows; start += ROWS_PER_PANE) {
    const span = Math.min(ROWS_PER_PANE, map.rows - start);
    const covered = Array.from({ length: span }, (_, i) => start + i);
    const style: CSSProperties = { gridRow: `${start + 1} / span ${span}` };

    if (!covered.some((r) => doorRows.left.has(r))) {
      items.push(
        <span key={`wl-${start}`} aria-hidden="true" className="window-pane" style={{ ...style, gridColumn: 1 }} />,
      );
    }
    if (!covered.some((r) => doorRows.right.has(r))) {
      items.push(
        <span
          key={`wr-${start}`}
          aria-hidden="true"
          className="window-pane"
          style={{ ...style, gridColumn: map.columns + 2 }}
        />,
      );
    }
  }

  grid.forEach((row, rIdx) => {
    if (fullRows.has(rIdx)) {
      // Rear bench: five across, no aisle. Rendered as its own strip so the
      // narrow aisle column does not squeeze the middle seat.
      items.push(
        <div
          key={`full-${rIdx}`}
          role="row"
          className="grid"
          style={{
            gridRow: rIdx + 1,
            gridColumn: `2 / span ${map.columns}`,
            gridTemplateColumns: `repeat(${map.columns}, minmax(0, 1fr))`,
            gap: "var(--gap)",
          }}
        >
          {row.map((cell, cIdx) => renderSeat(cell, rIdx, cIdx))}
        </div>,
      );
      return;
    }

    const doorCols = row.map((c, i) => (c.cell_type === "door" ? i : -1)).filter((i) => i >= 0);
    if (doorCols.length > 0) {
      const from = Math.min(...doorCols);
      items.push(
        <span
          key={`door-${rIdx}`}
          role="img"
          aria-label="Kirish eshigi"
          className="door-slot"
          style={{ gridRow: rIdx + 1, gridColumn: `${from + 2} / span ${doorCols.length}` }}
        >
          <DoorOpen size={14} weight="bold" />
          Kirish
        </span>,
      );
    }

    row.forEach((cell, cIdx) => {
      if (!cell.seat) return;
      items.push(renderSeat(cell, rIdx, cIdx, { gridRow: rIdx + 1, gridColumn: cIdx + 2 }));
    });
  });

  return (
    <div className="flex flex-col items-center">
      {hasWomenRows && (
        <p className="mb-5 flex items-center gap-2.5 rounded-full border border-women/40 bg-women-soft/90 px-4 py-2 text-[13px] font-medium leading-snug text-women backdrop-blur-md">
          <GenderFemale size={15} weight="bold" aria-hidden="true" />
          Oldingi qatorlar: faqat ayollar uchun joylar
        </p>
      )}

      <div className="w-full overflow-x-auto px-3 pb-2 pt-1">
        <div className="bus">
          <span aria-hidden="true" className="bus-wheel bus-wheel-l bus-wheel-front" />
          <span aria-hidden="true" className="bus-wheel bus-wheel-r bus-wheel-front" />
          <span aria-hidden="true" className="bus-wheel bus-wheel-l bus-wheel-rear" />
          <span aria-hidden="true" className="bus-wheel bus-wheel-r bus-wheel-rear" />

          <div className="bus-shell">
            <div className="bus-nose flex items-end justify-between px-5 pb-2">
              <span className="relative z-10 inline-flex items-center gap-1.5 text-[12px] font-semibold text-ink/70">
                <SteeringWheel size={22} weight="duotone" />
                Haydovchi
              </span>
              <span className="relative z-10 text-[11px] font-medium text-ink/50">old tomon</span>
            </div>

            <div
              role="grid"
              aria-label="Avtobus joylari sxemasi"
              className="seat-grid"
              style={{ gridTemplateColumns: columnTemplate }}
            >
              {items}
            </div>

            <div className="bus-tail" aria-hidden="true" />
          </div>
        </div>
      </div>

      <SeatLegend women={hasWomenRows} />
    </div>
  );
}

function SeatLegend({ women }: { women: boolean }) {
  const items = [
    { className: "seat", label: "Bo‘sh" },
    ...(women ? [{ className: "seat seat-women", label: "Ayollar uchun" }] : []),
    { className: "seat seat-picked", label: "Sizning tanlovingiz" },
    { className: "seat seat-taken", label: "Band" },
  ];
  return (
    <ul className="glass mt-5 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 rounded-full px-5 py-2.5">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-2 text-[13px] font-medium text-muted">
          <span aria-hidden="true" className={`${item.className} !h-4 !w-5 !rounded-[5px_5px_4px_4px] !shadow-none !animate-none before:!hidden`} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
