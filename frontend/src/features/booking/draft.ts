import type { PassengerIn } from "../../types/api";

export type DraftBooking = {
  requestKey?: string;
  tripId: string;
  seatIds: string[];
  seatNumbers: string[];
  passengers: PassengerIn[];
  phone: string;
};

const KEY = "nway_draft";

export function saveDraft(draft: DraftBooking): void {
  sessionStorage.setItem(KEY, JSON.stringify(draft));
}

export function loadDraft(): DraftBooking | null {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  return JSON.parse(raw) as DraftBooking;
}

export function clearDraft(): void {
  sessionStorage.removeItem(KEY);
}
