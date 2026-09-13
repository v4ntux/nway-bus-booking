import { useEffect, useRef, type ReactNode } from "react";
import { X } from "@phosphor-icons/react";

/**
 * Native <dialog>: focus trap, Esc to close and a backdrop for free.
 * Used by the admin for create / edit forms so tables stay uncluttered.
 */
export function Dialog({
  open,
  onClose,
  title,
  sub,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  sub?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      className={`dialog glass-strong m-auto w-[calc(100%-2rem)] rounded-plate p-0 text-ink shadow-lift backdrop:bg-ink/40 backdrop:backdrop-blur-sm ${
        wide ? "max-w-2xl" : "max-w-lg"
      }`}
    >
      {open && (
        <div className="flex flex-col gap-5 p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-[20px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>
              {sub && <p className="mt-1 text-[14px] text-muted">{sub}</p>}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Yopish"
              className="glass inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-[11px] text-muted transition-colors hover:text-ink"
            >
              <X size={16} weight="bold" />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}
