import { apiRequest } from "./client";
import type { MyReservation, PassengerIn, Payment, Reservation, Ticket } from "../types/api";

export const bookingApi = {
  createReservation: (body: {
    request_key?: string;
    trip_id: string;
    seat_ids: string[];
    contact_phone: string;
    passengers: PassengerIn[];
  }) =>
    apiRequest<Reservation>("/api/v1/reservations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getReservation: (code: string) => apiRequest<Reservation>(`/api/v1/reservations/${code}`),
  confirmCash: (code: string) => apiRequest<Reservation>(`/api/v1/reservations/${code}/confirm-cash`, { method: "POST" }),
  delivery: (code: string) => apiRequest<{ total: number; sent: number; failed: boolean }>(`/api/v1/reservations/${code}/telegram-delivery`),
  cancel: (code: string) =>
    apiRequest<Reservation>(`/api/v1/reservations/${code}/cancel`, { method: "POST" }),
  createPayment: (code: string, method: string, provider = "mock") =>
    apiRequest<Payment>(`/api/v1/reservations/${code}/payments`, {
      method: "POST",
      body: JSON.stringify({ method, provider }),
    }),
  mockSuccess: (paymentId: string) =>
    apiRequest<Payment>(`/api/v1/payments/${paymentId}/mock-success`, { method: "POST" }),
  lookup: (phone: string, public_code: string) =>
    apiRequest<Reservation>("/api/v1/bookings/lookup", {
      method: "POST",
      body: JSON.stringify({ phone, public_code }),
    }),
  mine: () => apiRequest<MyReservation[]>("/api/v1/me/reservations"),
  resendToTelegram: (code: string) =>
    apiRequest<{ queued: boolean }>(`/api/v1/reservations/${code}/telegram-resend`, { method: "POST" }),
  tickets: (code: string) => apiRequest<Ticket[]>(`/api/v1/reservations/${code}/tickets`),
  ticket: (publicId: string) => apiRequest<Ticket>(`/api/v1/tickets/${publicId}`),
};
