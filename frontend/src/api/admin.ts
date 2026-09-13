import { apiRequest } from "./client";
import type {
  AdminUser,
  Bus,
  BusIn,
  BusLayout,
  City,
  CityIn,
  Company,
  Dashboard,
  LayoutGenerateIn,
  Page,
  PassengerRow,
  Payment,
  Reservation,
  Route,
  RouteIn,
  TokenResponse,
  Trip,
  TripCreateIn,
  TripPatchIn,
} from "../types/api";

const json = (method: "POST" | "PATCH", body?: unknown) => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const authApi = {
  adminLogin: (email: string, password: string) =>
    apiRequest<TokenResponse>("/api/v1/auth/admin/login", json("POST", { email, password })),
};

export const adminApi = {
  dashboard: () => apiRequest<Dashboard>("/api/v1/admin/dashboard"),

  cities: () => apiRequest<City[]>("/api/v1/admin/cities"),
  createCity: (body: CityIn) => apiRequest<City>("/api/v1/admin/cities", json("POST", body)),
  patchCity: (id: string, body: CityIn) => apiRequest<City>(`/api/v1/admin/cities/${id}`, json("PATCH", body)),
  deactivateCity: (id: string) => apiRequest<City>(`/api/v1/admin/cities/${id}/deactivate`, json("POST")),

  routes: () => apiRequest<Route[]>("/api/v1/admin/routes"),
  createRoute: (body: RouteIn) => apiRequest<Route>("/api/v1/admin/routes", json("POST", body)),
  patchRoute: (id: string, body: RouteIn) =>
    apiRequest<Route>(`/api/v1/admin/routes/${id}`, json("PATCH", body)),
  deactivateRoute: (id: string) => apiRequest<Route>(`/api/v1/admin/routes/${id}/deactivate`, json("POST")),

  buses: () => apiRequest<Bus[]>("/api/v1/admin/buses"),
  createBus: (body: BusIn) => apiRequest<Bus>("/api/v1/admin/buses", json("POST", body)),
  patchBus: (id: string, body: BusIn) => apiRequest<Bus>(`/api/v1/admin/buses/${id}`, json("PATCH", body)),
  layout: (busId: string) => apiRequest<BusLayout>(`/api/v1/admin/buses/${busId}/layout`),
  generateLayout: (busId: string, body: LayoutGenerateIn) =>
    apiRequest<BusLayout>(`/api/v1/admin/buses/${busId}/layout`, json("POST", body)),
  patchLayoutCells: (busId: string, cells: { row: number; column: number; cell_type: string }[]) =>
    apiRequest<BusLayout>(`/api/v1/admin/buses/${busId}/layout/cells`, json("PATCH", cells)),

  trips: () => apiRequest<Trip[]>("/api/v1/admin/trips"),
  createTrip: (body: TripCreateIn) => apiRequest<Trip>("/api/v1/admin/trips", json("POST", body)),
  patchTrip: (id: string, body: TripPatchIn) => apiRequest<Trip>(`/api/v1/admin/trips/${id}`, json("PATCH", body)),
  cancelTrip: (id: string) => apiRequest<Trip>(`/api/v1/admin/trips/${id}/cancel`, json("POST")),
  changeBus: (id: string, bus_id: string) =>
    apiRequest<Trip>(`/api/v1/admin/trips/${id}/change-bus`, json("POST", { bus_id })),

  reservations: (params: URLSearchParams) =>
    apiRequest<Page<Reservation>>(`/api/v1/admin/reservations?${params.toString()}`),
  reservationAction: (id: string, action: string) =>
    apiRequest<Reservation>(`/api/v1/admin/reservations/${id}/${action}`, json("POST")),

  payments: (page = 1) => apiRequest<Page<Payment>>(`/api/v1/admin/payments?page=${page}&page_size=50`),
  passengers: (page = 1) =>
    apiRequest<Page<PassengerRow>>(`/api/v1/admin/passengers?page=${page}&page_size=50`),
  users: (page = 1) => apiRequest<Page<AdminUser>>(`/api/v1/admin/users?page=${page}&page_size=50`),

  companies: () => apiRequest<Page<Company>>("/api/v1/admin/companies?page_size=100"),
  createCompany: (body: { name: string; phone: string; active: boolean }) =>
    apiRequest<Company>("/api/v1/admin/companies", json("POST", body)),
};
