export const ERROR_UZ: Record<string, string> = {
  SEAT_ALREADY_RESERVED: "Bu joy allaqachon band qilindi. Boshqasini tanlang.",
  TRIP_NOT_BOOKABLE: "Bu reysga chipta sotilmaydi.",
  NO_SEATS: "Kamida bitta joy tanlang.",
  SEAT_NOT_BOOKABLE: "Bu joy mavjud emas.",
  SEAT_WRONG_BUS: "Joy bu avtobusga tegishli emas.",
  RESERVATION_EXPIRED: "Bron muddati tugadi. Joylar yana bo‘sh.",
  RESERVATION_NOT_FOUND: "Bron topilmadi. Telefon va kodni tekshiring.",
  INVALID_PHONE: "Raqam noto‘g‘ri. Namuna: +998 90 123 45 67",
  OTP_INVALID: "Kod noto‘g‘ri yoki muddati o‘tgan.",
  INVALID_CREDENTIALS: "Email yoki parol noto‘g‘ri.",
  PAYMENT_NOT_ALLOWED: "Bu buyurtma uchun to‘lov mavjud emas.",
  TICKET_ALREADY_USED: "Chipta allaqachon foydalanilgan.",
  TICKET_CANCELLED: "Chipta bekor qilingan.",
  TICKET_NOT_FOUND: "Chipta topilmadi.",
  VALIDATION_ERROR: "Kiritilgan ma’lumotlarni tekshiring.",
  UNAUTHORIZED: "Tizimga kirish kerak.",
  FORBIDDEN: "Ruxsat yetarli emas.",
  LAYOUT_IN_USE: "Bu avtobus joylariga bronlar bor, sxemani qayta qurish mumkin emas.",
  BUS_NOT_FOUND: "Avtobus topilmadi.",
  TRIP_NOT_FOUND: "Reys topilmadi.",
  ROUTE_NOT_FOUND: "Yo‘nalish topilmadi.",
  CITY_NOT_FOUND: "Shahar topilmadi.",
  HTTP_ERROR: "Server javob bermadi. Qayta urinib ko‘ring.",
};

export function errorMessage(code: string, fallback?: string): string {
  return ERROR_UZ[code] ?? fallback ?? "Nimadir xato ketdi. Qayta urinib ko‘ring.";
}

/*
 * Uzbek Latin names are spelled out by hand: not every browser ships ICU data
 * for "uz-Latn", and a fallback like "M09" on a ticket is not acceptable.
 * Prices group thousands with a space (180 000), as printed on real tickets.
 */
const MONTHS_LONG = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
];
const MONTHS_SHORT = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];
const WEEKDAYS_SHORT = ["yak", "dush", "sesh", "chor", "pay", "jum", "shan"];

export function formatNumber(value: number): string {
  const [int, frac] = Math.abs(value).toString().split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f");
  return `${value < 0 ? "-" : ""}${grouped}${frac ? `,${frac}` : ""}`;
}

export function formatMoney(amountMinor: number, currency: string): string {
  return `${formatNumber(Math.round(amountMinor / 100))} ${currency}`;
}

/*
 * Departure and arrival are stored UTC. A passenger reads the clock of the
 * city they are standing in, so every trip time renders in its own city zone.
 */

type Parts = { year: number; month: number; day: number; weekday: number; hour: string; minute: string };

function parts(iso: string, timeZone: string | undefined): Parts {
  const date = new Date(iso);
  const read = (tz: string) =>
    new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      year: "numeric",
      month: "numeric",
      day: "numeric",
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).formatToParts(date);
  let list: Intl.DateTimeFormatPart[];
  try {
    list = read(timeZone || "UTC");
  } catch {
    list = read("UTC");
  }
  const get = (type: Intl.DateTimeFormatPartTypes) => list.find((p) => p.type === type)?.value ?? "";
  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  return {
    year: Number(get("year")),
    month: Number(get("month")) - 1,
    day: Number(get("day")),
    weekday: Math.max(0, weekdays.indexOf(get("weekday"))),
    // Some engines print midnight as "24".
    hour: get("hour") === "24" ? "00" : get("hour"),
    minute: get("minute"),
  };
}

/** `07:30` in the given city's zone. */
export function formatClock(iso: string, timeZone?: string): string {
  const p = parts(iso, timeZone);
  return `${p.hour}:${p.minute}`;
}

/** `pay, 14-avg` in the given city's zone. */
export function formatDayLabel(iso: string, timeZone?: string): string {
  const p = parts(iso, timeZone);
  return `${WEEKDAYS_SHORT[p.weekday]}, ${p.day}-${MONTHS_SHORT[p.month]}`;
}

/** `14-avgust 2026, 07:30` for receipts. */
export function formatDateTimeLong(iso: string, timeZone?: string): string {
  const p = parts(iso, timeZone);
  return `${p.day}-${MONTHS_LONG[p.month]} ${p.year}, ${p.hour}:${p.minute}`;
}

/** `Sentabr 2026` for calendar headers. */
export function formatMonthTitle(date: Date): string {
  const name = MONTHS_LONG[date.getMonth()];
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} ${date.getFullYear()}`;
}

/** `shan, 7-sen` for a local calendar date (no zone shift). */
export function formatLocalDay(date: Date): string {
  return `${WEEKDAYS_SHORT[date.getDay()]}, ${date.getDate()}-${MONTHS_SHORT[date.getMonth()]}`;
}

export function formatDateTime(iso: string): string {
  return formatDateTimeLong(iso, "Asia/Tashkent");
}

/** `2026-08-14` for query strings and date inputs. */
export function toDateInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** `9 soat 40 daq`: travel time reads better than a raw minute count. */
export function formatDuration(minutes: number): string {
  const total = Math.max(0, Math.round(minutes));
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h === 0) return `${m} daq`;
  if (m === 0) return `${h} soat`;
  return `${h} soat ${m} daq`;
}

export function durationBetween(fromIso: string, toIso: string): number {
  return (new Date(toIso).getTime() - new Date(fromIso).getTime()) / 60000;
}

/** `mm:ss` for the booking hold countdown. */
export function formatCountdown(msLeft: number): string {
  const total = Math.max(0, Math.floor(msLeft / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** Uzbek counts with a classifier: 1 ta joy, 5 ta joy. */
export function seatsWord(n: number): string {
  return `${n} ta joy`;
}

export function tripsWord(n: number): string {
  return `${n} ta reys`;
}

/** `+998 90 123 45 67` while typing, digits preserved for the API. */
export function formatPhoneDisplay(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  const body = digits.slice(0, 12);
  const groups = [body.slice(0, 3), body.slice(3, 5), body.slice(5, 8), body.slice(8, 10), body.slice(10, 12)];
  return `+${groups.filter(Boolean).join(" ")}`;
}

export function phoneToApi(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  return digits ? `+${digits}` : "";
}

export const PAYMENT_PROVIDER_UZ: Record<string, string> = {
  payme: "Payme",
  click: "Click",
  card: "Uzcard / Humo",
  mock: "Onlayn",
  offline: "Naqd",
};

export const PAYMENT_METHOD_UZ: Record<string, string> = {
  online: "onlayn",
  card: "karta",
  cash: "naqd",
  transfer: "o‘tkazma",
};
