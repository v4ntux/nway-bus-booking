import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowsClockwise, DoorOpen, GenderFemale, SteeringWheel } from "@phosphor-icons/react";
import { adminApi } from "../../api/admin";
import { ApiError } from "../../api/client";
import { AdminHeader } from "../../components/Table";
import { Button, ErrorBox, Field, Input, Skeleton, backLinkClass } from "../../components/Ui";
import type { BusLayout, LayoutGenerateIn } from "../../types/api";

/** "1, 3-4" -> [0, 2, 3]. Operators count from 1; the API counts from 0. */
function parseList(raw: string): number[] {
  const out = new Set<number>();
  raw.split(/[,\s]+/).forEach((part) => {
    if (!part) return;
    const [a, b] = part.split("-").map((n) => Number(n));
    if (Number.isNaN(a)) return;
    const end = Number.isNaN(b) || b === undefined ? a : b;
    for (let i = Math.min(a, end); i <= Math.max(a, end); i += 1) out.add(i - 1);
  });
  return [...out].filter((n) => n >= 0).sort((x, y) => x - y);
}

function GenerateForm({
  busId,
  exists,
  onDone,
}: {
  busId: string;
  exists: boolean;
  onDone: () => void;
}) {
  const [rows, setRows] = useState("13");
  const [columns, setColumns] = useState("5");
  const [aisle, setAisle] = useState("3");
  const [doorRows, setDoorRows] = useState("2, 12");
  const [fullRows, setFullRows] = useState("13");
  const [womenRows, setWomenRows] = useState("1-4");
  const [name, setName] = useState("2+2 salon");

  const mutation = useMutation({
    mutationFn: (body: LayoutGenerateIn) => adminApi.generateLayout(busId, body),
    onSuccess: onDone,
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    const cols = Number(columns);
    const aisleCols = parseList(aisle);
    const lastAisle = aisleCols.length ? Math.max(...aisleCols) : Math.floor(cols / 2);
    // Kerb-side doors take the seat columns right of the aisle.
    const doorCols = Array.from({ length: cols - lastAisle - 1 }, (_, i) => lastAisle + 1 + i).slice(0, 2);
    const door_cells = parseList(doorRows).flatMap((r) => doorCols.map((c) => [r, c] as [number, number]));
    mutation.mutate({
      name: name.trim() || "Salon",
      rows: Number(rows),
      columns: cols,
      aisle_columns: aisleCols,
      door_cells,
      full_width_rows: parseList(fullRows),
      women_rows: parseList(womenRows),
    });
  }

  return (
    <form onSubmit={submit} className="glass flex flex-col gap-4 rounded-panel p-4 sm:p-5">
      <div>
        <h2 className="text-[17px] font-semibold text-ink">{exists ? "Sxemani qayta qurish" : "Sxemani qurish"}</h2>
        <p className="mt-1 text-[13.5px] leading-relaxed text-muted">
          Qatorlar 1 dan boshlab sanaladi. Eshik qatorlarida yo‘lakning o‘ng tomonidagi joylar kirishga
          beriladi, oxirgi qator to‘liq kenglikda 5 ta joy bo‘ladi.
          {exists && " Bronlangan joylari bor avtobus sxemasini qayta qurish mumkin emas."}
        </p>
      </div>
      {mutation.isError && <ErrorBox error={mutation.error} />}
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Qatorlar" htmlFor="g-rows">
          <Input id="g-rows" value={rows} onChange={(e) => setRows(e.target.value)} inputMode="numeric" className="tnum" required />
        </Field>
        <Field label="Ustunlar" hint="Yo‘lak bilan birga" htmlFor="g-cols">
          <Input id="g-cols" value={columns} onChange={(e) => setColumns(e.target.value)} inputMode="numeric" className="tnum" required />
        </Field>
        <Field label="Yo‘lak ustuni" htmlFor="g-aisle">
          <Input id="g-aisle" value={aisle} onChange={(e) => setAisle(e.target.value)} className="tnum" required />
        </Field>
        <Field label="Eshik qatorlari" hint="Masalan 2, 12" htmlFor="g-doors">
          <Input id="g-doors" value={doorRows} onChange={(e) => setDoorRows(e.target.value)} className="tnum" />
        </Field>
        <Field label="To‘liq qatorlar" hint="Orqa o‘rindiq" htmlFor="g-full">
          <Input id="g-full" value={fullRows} onChange={(e) => setFullRows(e.target.value)} className="tnum" />
        </Field>
        <Field label="Ayollar qatorlari" hint="Masalan 1-4" htmlFor="g-women">
          <Input id="g-women" value={womenRows} onChange={(e) => setWomenRows(e.target.value)} className="tnum" />
        </Field>
      </div>
      <Field label="Sxema nomi" htmlFor="g-name">
        <Input id="g-name" value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Button type="submit" loading={mutation.isPending} icon={<ArrowsClockwise size={16} weight="bold" />} className="self-start">
        {exists ? "Qayta qurish" : "Qurish"}
      </Button>
    </form>
  );
}

function Preview({ layout }: { layout: BusLayout }) {
  const grid = useMemo(() => {
    const byPos = new Map<string, BusLayout["cells"][number]>();
    layout.cells.forEach((c) => byPos.set(`${c.row}:${c.column}`, c));
    const seatNumber = new Map<string, number>();
    let n = 0;
    for (let r = 0; r < layout.rows; r += 1) {
      for (let c = 0; c < layout.columns; c += 1) {
        const cell = byPos.get(`${r}:${c}`);
        if (cell?.seat_id) {
          n += 1;
          seatNumber.set(cell.seat_id, n);
        }
      }
    }
    return { byPos, seatNumber, total: n };
  }, [layout]);

  return (
    <div className="glass flex flex-col items-center gap-4 rounded-panel p-4 sm:p-6">
      <div className="flex w-full items-center justify-between text-[13px] text-muted">
        <span className="inline-flex items-center gap-1.5">
          <SteeringWheel size={16} weight="duotone" /> Haydovchi oldinda
        </span>
        <span className="tnum">{grid.total} joy</span>
      </div>
      <div className="overflow-x-auto">
        <div className="bus-shell mx-auto w-fit !rounded-[28px] p-3">
          <div className="flex flex-col gap-1.5">
            {Array.from({ length: layout.rows }).map((_, r) => (
              <div key={r} className="flex gap-1.5">
                {Array.from({ length: layout.columns }).map((_, c) => {
                  const cell = grid.byPos.get(`${r}:${c}`);
                  if (cell?.seat_id) {
                    return (
                      <div key={c} className="seat tnum h-11 w-11 text-[13px]" title={`${r + 1}-qator`}>
                        {grid.seatNumber.get(cell.seat_id)}
                      </div>
                    );
                  }
                  if (cell?.cell_type === "door") {
                    return (
                      <div key={c} className="door-slot h-11 w-11 !text-[10px]">
                        <DoorOpen size={14} weight="bold" />
                      </div>
                    );
                  }
                  if (cell?.cell_type === "aisle") {
                    return <div key={c} aria-hidden="true" className="aisle-lane h-11 w-11 !rounded-[10px]" />;
                  }
                  return <div key={c} aria-hidden="true" className="h-11 w-11" />;
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
      <p className="inline-flex items-center gap-1.5 text-[12.5px] text-faint">
        <GenderFemale size={14} weight="bold" /> Ayollar qatorlari yo‘lovchi sxemasida alohida rangda ko‘rinadi.
      </p>
    </div>
  );
}

export function LayoutPage() {
  const { busId = "" } = useParams();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["layout", busId],
    queryFn: () => adminApi.layout(busId),
    retry: false,
  });
  const bus = useQuery({ queryKey: ["admin-buses"], queryFn: adminApi.buses });
  const current = bus.data?.find((b) => b.id === busId);
  const layout = query.data;
  const missing = query.isError && query.error instanceof ApiError && query.error.code === "LAYOUT_NOT_FOUND";

  return (
    <>
      <Link to="/admin/buses" className={backLinkClass}>
        <ArrowLeft size={15} weight="bold" />
        Avtobuslarga
      </Link>

      <AdminHeader
        title={current ? `${current.name}, salon sxemasi` : "Salon sxemasi"}
        sub={layout ? `${layout.name}: ${layout.rows} qator, ${layout.columns} ustun` : current?.model}
      />

      {query.isError && !missing && <ErrorBox error={query.error} />}
      {query.isLoading && <Skeleton className="h-96 w-full" />}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {layout && <Preview layout={layout} />}
        {missing && (
          <div className="glass flex flex-col items-center justify-center gap-2 rounded-panel border-dashed p-8 text-center">
            <p className="text-[15px] font-medium text-ink">Bu avtobusda hali sxema yo‘q</p>
            <p className="max-w-[36ch] text-[13.5px] text-muted">
              Yonidagi shakl orqali quring. Standart: 13 qator, 2+2 va orqa o‘rindiq.
            </p>
          </div>
        )}
        {(layout || missing) && (
          <GenerateForm
            busId={busId}
            exists={Boolean(layout)}
            onDone={() => {
              client.invalidateQueries({ queryKey: ["layout", busId] });
              client.invalidateQueries({ queryKey: ["admin-buses"] });
            }}
          />
        )}
      </div>
    </>
  );
}
