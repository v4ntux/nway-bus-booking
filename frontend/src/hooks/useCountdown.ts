import { useEffect, useState } from "react";

/**
 * Ticks once a second toward an ISO deadline. Returns milliseconds left and
 * whether the deadline has passed, so the hold on a seat is visible instead
 * of expiring silently under the passenger.
 */
export function useCountdown(deadlineIso: string | null | undefined) {
  const target = deadlineIso ? new Date(deadlineIso).getTime() : null;
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!target) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [target]);

  if (!target) return { msLeft: null, expired: false } as const;
  const msLeft = Math.max(0, target - now);
  return { msLeft, expired: msLeft === 0 } as const;
}
