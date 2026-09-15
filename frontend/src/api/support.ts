import { apiRequest } from "./client";
import type { AppConfig, FaqItem, FaqIn, FaqLang } from "../types/api";

const json = (method: "POST" | "PATCH", body: unknown) => ({ method, body: JSON.stringify(body) });

export const supportApi = {
  appConfig: () => apiRequest<AppConfig>("/api/v1/app-config"),
  faq: (lang: FaqLang) => apiRequest<FaqItem[]>(`/api/v1/faq?lang=${lang}`),
};

export const faqAdminApi = {
  list: () => apiRequest<FaqItem[]>("/api/v1/admin/faq"),
  create: (body: FaqIn) => apiRequest<FaqItem>("/api/v1/admin/faq", json("POST", body)),
  patch: (id: string, body: FaqIn) => apiRequest<FaqItem>(`/api/v1/admin/faq/${id}`, json("PATCH", body)),
  remove: (id: string) => apiRequest<void>(`/api/v1/admin/faq/${id}`, { method: "DELETE" }),
};
