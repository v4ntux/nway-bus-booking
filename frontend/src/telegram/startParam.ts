import { toDateInput } from "../utils/format";

/** Mirrors backend app/utils/startapp.py: a UUID is 22 chars of base64url. */
function uuidFromBase64Url(value: string): string | null {
  if (value.length !== 22) return null;
  try {
    const binary = atob(value.replace(/-/g, "+").replace(/_/g, "/") + "==");
    if (binary.length !== 16) return null;
    const hex = Array.from(binary, (ch) => ch.charCodeAt(0).toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  } catch {
    return null;
  }
}

/** Where a `t.me/<bot>?startapp=<param>` link should land inside the Mini App. */
export function startParamPath(param: string | undefined, today = toDateInput(new Date())): string | null {
  if (!param) return null;
  if (param === "my" || param === "tickets") return "/my";
  if (param === "faq" || param === "support") return "/faq";
  if (param === "book") return "/book";
  if (param.startsWith("t_") && /^t_[A-Z0-9]{9}$/.test(param)) return `/ticket/${param.slice(2)}`;
  if (param.length === 45 && param.startsWith("r")) {
    const origin = uuidFromBase64Url(param.slice(1, 23));
    const dest = uuidFromBase64Url(param.slice(23));
    if (origin && dest) return `/trips?origin=${origin}&dest=${dest}&date=${today}`;
  }
  return null;
}
