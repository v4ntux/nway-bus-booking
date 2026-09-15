export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ErrorEnvelope = {
  error: { code: string; message: string };
};

function getToken(): string | null {
  return localStorage.getItem("nway_access_token");
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem("nway_access_token", access);
  localStorage.setItem("nway_refresh_token", refresh);
}

export function clearTokens(): void {
  localStorage.removeItem("nway_access_token");
  localStorage.removeItem("nway_refresh_token");
}

const BOOKING_PHONE_KEY = "nway_booking_phone";

/** Web bookings are opened with code + contact phone; the code alone is not enough. */
export function rememberBookingPhone(phone: string): void {
  try {
    localStorage.setItem(BOOKING_PHONE_KEY, phone);
  } catch {
    /* storage blocked: lookup by phone still works */
  }
}

function bookingPhone(): string | null {
  try {
    return localStorage.getItem(BOOKING_PHONE_KEY);
  } catch {
    return null;
  }
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  const telegramData = window.Telegram?.WebApp?.initData;
  if (telegramData) headers.set("X-Telegram-Init-Data", telegramData);
  const phone = telegramData ? null : bookingPhone();
  if (phone) headers.set("X-Booking-Phone", phone);
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let code = "HTTP_ERROR";
    let message = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as ErrorEnvelope;
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
    } catch {
      /* ignore non-json */
    }
    throw new ApiError(code, message, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
