import {
  cloneElement,
  isValidElement,
  useId,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type PointerEvent as ReactPointerEvent,
  type ReactElement,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import { CaretDown, CircleNotch, Warning } from "@phosphor-icons/react";
import { errorMessage, formatNumber } from "../utils/format";
import { ApiError } from "../api/client";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const VARIANT: Record<Variant, string> = {
  primary: "btn-sun hover:-translate-y-0.5 active:translate-y-px active:scale-[0.99]",
  secondary:
    "glass text-ink hover:-translate-y-0.5 hover:border-accent/40 active:translate-y-px active:scale-[0.99]",
  ghost: "bg-transparent text-muted border border-transparent hover:bg-surface/60 hover:text-ink",
  danger:
    "bg-danger text-white border border-danger shadow-raise hover:bg-danger/90 hover:-translate-y-0.5 active:translate-y-px",
};

const SIZE: Record<Size, string> = {
  sm: "h-9 px-3 text-sm gap-1.5 rounded-[11px]",
  md: "h-11 px-4 text-[15px] gap-2 rounded-control",
  lg: "h-14 px-6 text-base gap-2.5 rounded-control",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  loading?: boolean;
  icon?: ReactNode;
};

export function Button({
  variant = "primary",
  size = "md",
  block = false,
  loading = false,
  icon,
  children,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex shrink-0 items-center justify-center whitespace-nowrap font-semibold transition-all duration-300 ease-out disabled:pointer-events-none disabled:opacity-45 ${VARIANT[variant]} ${SIZE[size]} ${block ? "w-full" : ""} ${className}`}
    >
      {loading ? <CircleNotch size={18} weight="bold" className="animate-spin" /> : icon}
      {children}
    </button>
  );
}

export function followSpot(event: ReactPointerEvent<HTMLElement>) {
  const box = event.currentTarget.getBoundingClientRect();
  event.currentTarget.style.setProperty("--sx", `${event.clientX - box.left}px`);
  event.currentTarget.style.setProperty("--sy", `${event.clientY - box.top}px`);
}

export const inputClass =
  "well h-12 w-full rounded-control px-3.5 text-[15px] text-ink transition-[border-color,box-shadow,background-color] duration-200 ease-out hover:border-accent/40 focus:border-accent focus:bg-surface focus:outline-none focus:shadow-[0_0_0_4px_rgb(var(--c-accent)/0.2)] disabled:opacity-50";

export const selectClass = `${inputClass} cursor-pointer appearance-none pr-10`;

export function Field({
  label,
  hint,
  error,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  const hintId = useId();
  const errorId = useId();
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<{ "aria-invalid"?: boolean; "aria-describedby"?: string }>, {
        "aria-invalid": error ? true : undefined,
        "aria-describedby": describedBy,
      })
    : children;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={htmlFor} className="text-sm font-medium text-ink">
        {label}
      </label>
      {hint && (
        <p id={hintId} className="-mt-1 text-[13px] text-muted">
          {hint}
        </p>
      )}
      {control}
      {error && (
        <p id={errorId} role="alert" className="text-[13px] font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${className}`} />;
}

export function Select({ className = "", children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select {...props} className={`${selectClass} ${className}`}>
        {children}
      </select>
      <CaretDown
        size={16}
        weight="bold"
        aria-hidden="true"
        className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-muted"
      />
    </div>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null;
  const code = error instanceof ApiError ? error.code : "UNKNOWN";
  const fallback = error instanceof Error ? error.message : undefined;
  return (
    <div
      role="alert"
      className="flex animate-fade-rise items-start gap-3 rounded-panel border border-danger/30 bg-danger-soft/90 p-4 backdrop-blur-md"
    >
      <Warning size={20} weight="fill" className="mt-0.5 shrink-0 text-danger" />
      <p className="text-[15px] leading-snug text-ink">{errorMessage(code, fallback)}</p>
    </div>
  );
}

const TONE = {
  neutral: "bg-surface/70 text-muted border-line",
  accent: "bg-accent-soft text-accent-strong border-accent/40",
  sky: "bg-sky-soft text-sky-ink border-sky/30",
  positive: "bg-positive-soft text-positive border-positive/30",
  danger: "bg-danger-soft text-danger border-danger/30",
} as const;

export type Tone = keyof typeof TONE;

export function Badge({
  tone = "neutral",
  children,
  className = "",
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONE[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Panel({
  children,
  className = "",
  as: As = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "li";
}) {
  return <As className={`glass rounded-panel ${className}`}>{children}</As>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

export function Spinner({ className = "" }: { className?: string }) {
  return <CircleNotch size={20} weight="bold" className={`animate-spin text-muted ${className}`} />;
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon?: ReactNode;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="glass flex animate-fade-rise flex-col items-center gap-3 rounded-panel border-dashed px-6 py-14 text-center">
      {icon && <div className="text-faint">{icon}</div>}
      <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
      {body && <p className="max-w-[42ch] text-[15px] leading-relaxed text-muted">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function PageTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className="text-[26px] font-semibold leading-tight tracking-[-0.02em] text-ink sm:text-[32px]">
        {children}
      </h1>
      {sub && <p className="text-[15px] text-muted">{sub}</p>}
    </div>
  );
}

export const backLinkClass =
  "inline-flex items-center gap-1.5 self-start text-[14px] font-medium text-muted no-underline transition-colors duration-200 hover:text-ink";

export function Amount({
  minor,
  currency,
  className = "",
}: {
  minor: number;
  currency: string;
  className?: string;
}) {
  return (
    <span className={`tnum ${className}`}>
      {formatNumber(Math.round(minor / 100))}
      <span className="ml-1 text-[0.72em] font-medium text-muted">{currency}</span>
    </span>
  );
}
