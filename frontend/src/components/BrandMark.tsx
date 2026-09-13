import { Link } from "react-router-dom";

/** Two dots are the route: saffron leaves at dusk, lapis arrives at night. */
function Mark({ compact }: { compact: boolean }) {
  return (
    <span aria-hidden="true" className="inline-flex items-center">
      <span
        className={`rounded-full bg-accent shadow-[0_0_10px_rgb(var(--c-accent)/0.6)] ${compact ? "h-1.5 w-1.5" : "h-2 w-2"}`}
      />
      <span
        className={`mx-0.5 h-px bg-gradient-to-r from-accent to-sky ${compact ? "w-2.5" : "w-3.5"}`}
      />
      <span
        className={`rounded-full bg-sky shadow-[0_0_10px_rgb(var(--c-sky)/0.6)] ${compact ? "h-1.5 w-1.5" : "h-2 w-2"}`}
      />
    </span>
  );
}

export function BrandMark({
  to = "/",
  size = "md",
}: {
  to?: string;
  size?: "sm" | "md";
}) {
  const compact = size === "sm";
  return (
    <Link
      to={to}
      viewTransition
      className="inline-flex items-center gap-2 no-underline transition-opacity duration-200 ease-out hover:opacity-70"
    >
      <Mark compact={compact} />
      <span
        className={`font-semibold tracking-tight text-ink ${compact ? "text-[15px]" : "text-[17px]"}`}
      >
        nway
      </span>
    </Link>
  );
}

export function BrandWord({ size = "md" }: { size?: "sm" | "md" }) {
  const compact = size === "sm";
  return (
    <span className="inline-flex items-center gap-2">
      <Mark compact={compact} />
      <span
        className={`font-semibold tracking-tight text-ink ${compact ? "text-[15px]" : "text-[17px]"}`}
      >
        nway
      </span>
    </span>
  );
}
