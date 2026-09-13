import { apiRequest } from "./client";
import type { PassengerIn, Payment, Reservation, Ticket } from "../types/api";

export const bookingApi = {
  createReservation: (body: {
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
  tickets: (code: string) => apiRequest<Ticket[]>(`/api/v1/reservations/${code}/tickets`),
  ticket: (publicId: string) => apiRequest<Ticket>(`/api/v1/tickets/${publicId}`),
};
