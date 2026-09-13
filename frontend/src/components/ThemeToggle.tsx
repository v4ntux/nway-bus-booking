import { useEffect, useState } from "react";
import { Moon, Sun } from "@phosphor-icons/react";

type Mode = "light" | "dark";
const KEY = "nway_theme";

function systemMode(): Mode {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * The page follows the OS until the passenger overrides it. Bus stations are
 * bright at noon and dark at 04:00, so both modes are first-class.
 */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const [mode, setMode] = useState<Mode>(() => {
    const stored = localStorage.getItem(KEY);
    return stored === "light" || stored === "dark" ? stored : systemMode();
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", mode);
    localStorage.setItem(KEY, mode);
  }, [mode]);

  const next = mode === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => setMode(next)}
      aria-label={next === "dark" ? "Tungi rejim" : "Kunduzgi rejim"}
      className={`glass inline-flex h-10 w-10 items-center justify-center rounded-control text-muted transition-all duration-300 ease-out hover:-translate-y-0.5 hover:border-accent/40 hover:text-ink ${className}`}
    >
      <span key={mode} className="inline-flex animate-icon-swap">
        {mode === "dark" ? <Sun size={18} weight="bold" /> : <Moon size={18} weight="bold" />}
      </span>
    </button>
  );
}
