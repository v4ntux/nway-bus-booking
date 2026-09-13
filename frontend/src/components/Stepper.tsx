import { Check } from "@phosphor-icons/react";

const STEPS = ["Reys", "Joylar", "Ma’lumotlar", "To‘lov"] as const;

/**
 * Booking is four moves. The passenger should never have to guess how many
 * are left, so the flow carries its own position marker.
 */
export function Stepper({ current }: { current: 0 | 1 | 2 | 3 }) {
  return (
    <nav aria-label="Bron qadamlari" className="flex items-center gap-1.5 sm:gap-2">
      {STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <div key={label} className="flex min-w-0 flex-1 items-center gap-1.5 sm:gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <span
                aria-hidden="true"
                className={`tnum flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold transition-all duration-300 ease-out ${
                  done
                    ? "border-accent/60 bg-accent-soft text-accent-strong"
                    : active
                      ? "btn-sun shadow-glow"
                      : "border-line bg-surface/60 text-faint"
                }`}
              >
                {done ? <Check size={12} weight="bold" /> : i + 1}
              </span>
              <span
                className={`truncate text-[13px] transition-colors duration-300 ${
                  active ? "font-semibold text-ink" : "text-muted"
                }`}
                aria-current={active ? "step" : undefined}
              >
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <span
                aria-hidden="true"
                className={`h-px min-w-2 flex-1 transition-colors duration-300 ${done ? "bg-accent/60" : "bg-line"}`}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
