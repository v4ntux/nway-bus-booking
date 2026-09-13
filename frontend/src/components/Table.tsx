import type { ReactNode, ThHTMLAttributes, TdHTMLAttributes } from "react";
import { Badge, Skeleton, type Tone } from "./Ui";

/*
 * Admin data density: hairlines between rows, no card per record, numbers in
 * mono so columns of codes, seats and money scan vertically.
 */

export function Table({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`glass overflow-x-auto rounded-panel ${className}`}>
      <table className="w-full border-collapse text-left text-[14px]">{children}</table>
    </div>
  );
}

export function Th({ className = "", children, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      {...props}
      className={`whitespace-nowrap border-b border-line/80 bg-surface/40 px-4 py-2.5 text-[12px] font-semibold text-muted ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({ className = "", children, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td {...props} className={`border-b border-hairline/80 px-4 py-3 align-middle text-ink ${className}`}>
      {children}
    </td>
  );
}

export function Tr({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <tr className={`transition-colors duration-150 hover:bg-surface/40 [&:last-child>td]:border-b-0 ${className}`}>
      {children}
    </tr>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="glass flex flex-col gap-2 rounded-panel p-4">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-6 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function TableEmpty({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-10 text-center text-[14px] text-muted">
        {children}
      </td>
    </tr>
  );
}

export const RESERVATION_STATUS_UZ: Record<string, { label: string; tone: Tone }> = {
  pending: { label: "to‘lov kutilmoqda", tone: "accent" },
  confirmed: { label: "tasdiqlangan", tone: "positive" },
  awaiting_admin_approval: { label: "tasdiqlash kutilmoqda", tone: "accent" },
  awaiting_deposit: { label: "oldindan to‘lov kerak", tone: "accent" },
  cancelled: { label: "bekor qilingan", tone: "danger" },
  expired: { label: "muddati tugagan", tone: "neutral" },
  completed: { label: "yakunlangan", tone: "neutral" },
  no_show: { label: "kelmadi", tone: "danger" },
};

export const PAYMENT_STATUS_UZ: Record<string, { label: string; tone: Tone }> = {
  paid: { label: "to‘langan", tone: "positive" },
  pending: { label: "kutilmoqda", tone: "accent" },
  unpaid: { label: "to‘lanmagan", tone: "neutral" },
  partially_paid: { label: "qisman", tone: "accent" },
  failed: { label: "xato", tone: "danger" },
  refunded: { label: "qaytarilgan", tone: "neutral" },
};

export const TRIP_STATUS_UZ: Record<string, { label: string; tone: Tone }> = {
  draft: { label: "qoralama", tone: "neutral" },
  scheduled: { label: "jadvalda", tone: "positive" },
  boarding: { label: "chiqish", tone: "accent" },
  departed: { label: "yo‘lda", tone: "sky" },
  completed: { label: "yetib keldi", tone: "neutral" },
  cancelled: { label: "bekor qilingan", tone: "danger" },
};

export function StatusBadge({
  status,
  kind = "reservation",
}: {
  status: string;
  kind?: "reservation" | "payment" | "trip";
}) {
  const map = kind === "payment" ? PAYMENT_STATUS_UZ : kind === "trip" ? TRIP_STATUS_UZ : RESERVATION_STATUS_UZ;
  const entry = map[status] ?? { label: status, tone: "neutral" as Tone };
  return <Badge tone={entry.tone}>{entry.label}</Badge>;
}

export function ActiveBadge({ active }: { active: boolean }) {
  return <Badge tone={active ? "positive" : "neutral"}>{active ? "faol" : "o‘chirilgan"}</Badge>;
}

export function AdminHeader({ title, sub, action }: { title: string; sub?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-ink sm:text-[28px]">{title}</h1>
        {sub && <p className="mt-1 text-[14px] text-muted">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

/** Small inline action used in table rows. */
export function RowAction({
  children,
  onClick,
  tone = "default",
  disabled,
}: {
  children: ReactNode;
  onClick: () => void;
  tone?: "default" | "danger";
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-[10px] border px-2.5 text-[13px] font-medium transition-colors duration-200 disabled:opacity-40 ${
        tone === "danger"
          ? "border-transparent text-muted hover:border-danger/40 hover:bg-danger-soft hover:text-danger"
          : "border-line/80 bg-surface/60 text-ink hover:border-accent/50 hover:bg-accent-soft/70"
      }`}
    >
      {children}
    </button>
  );
}
