import { apiRequest } from "./client";
import type { City, Route, SeatMap, Trip } from "../types/api";

export const catalogApi = {
  cities: () => apiRequest<City[]>("/api/v1/cities"),
  routes: () => apiRequest<Route[]>("/api/v1/routes"),
  searchTrips: (originCityId: string, destinationCityId: string, travelDate: string) =>
    apiRequest<{ items: Trip[] }>(
      `/api/v1/trips?origin_city_id=${originCityId}&destination_city_id=${destinationCityId}&travel_date=${travelDate}`,
    ),
  trip: (id: string) => apiRequest<Trip>(`/api/v1/trips/${id}`),
  seats: (tripId: string) => apiRequest<SeatMap>(`/api/v1/trips/${tripId}/seats`),
};
