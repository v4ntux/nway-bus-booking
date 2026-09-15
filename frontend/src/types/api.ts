export type City = {
  id: string;
  name: string;
  country: string;
  timezone: string;
  active: boolean;
};

export type Route = {
  id: string;
  origin_city_id: string;
  destination_city_id: string;
  origin_city: City | null;
  destination_city: City | null;
  estimated_duration_minutes: number;
  distance_km: number;
  description: string | null;
  active: boolean;
  company_id: string;
};

export type Bus = {
  id: string;
  company_id: string;
  name: string;
  registration_number: string;
  model: string;
  seat_count: number;
  layout_type: string;
  active: boolean;
};

export type Trip = {
  id: string;
  route_id: string;
  bus_id: string;
  company_id: string;
  departure_datetime: string;
  estimated_arrival_datetime: string;
  status: string;
  base_price_minor: number;
  currency: string;
  boarding_location: string | null;
  destination_location: string | null;
  available_seats: number | null;
  route: Route | null;
  bus: Bus | null;
};

export type SeatStatus = "available" | "reserved" | "blocked" | "selected";

export type SeatInfo = {
  id: string;
  seat_number: string;
  type: string;
  status: SeatStatus;
  is_accessibility: boolean;
  is_premium: boolean;
  is_women_only?: boolean;
};

export type SeatCell = {
  row: number;
  column: number;
  cell_type: string;
  seat: SeatInfo | null;
};

export type SeatMap = {
  trip_id: string;
  rows: number;
  columns: number;
  cells: SeatCell[];
};

export type PassengerIn = {
  seat_id: string;
  first_name: string;
  last_name?: string;
  phone?: string;
};

export type Reservation = {
  id: string;
  public_code: string;
  trip_id: string;
  company_id: string;
  status: string;
  payment_status: string;
  payment_method: string | null;
  total_amount_minor: number;
  currency: string;
  expires_at: string | null;
  contact_phone: string;
  deposit_required: boolean;
  deposit_received: boolean;
  created_at: string;
  seats: { seat_id: string; price_minor: number; is_active_hold: boolean; seat_number: string | null }[];
  passengers: {
    id: string;
    seat_id: string;
    first_name: string;
    last_name: string | null;
    phone: string | null;
  }[];
  payments: Payment[];
};

export type Payment = {
  id: string;
  reservation_id: string;
  provider: string;
  method: string;
  amount_minor: number;
  currency: string;
  status: string;
  created_at: string;
  paid_at: string | null;
};

export type Ticket = {
  id: string;
  public_id: string;
  qr_token: string;
  reservation_id: string;
  trip_id: string;
  seat_id: string;
  status: string;
  passenger: { first_name: string; last_name: string | null } | null;
  seat_number: string | null;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    phone: string;
    email: string | null;
    role: string;
    company_id: string | null;
    first_name: string | null;
    last_name: string | null;
  };
};

export type Dashboard = {
  trips_today: number;
  passengers_today: number;
  sold_seats: number;
  free_seats: number;
  pending_approvals: number;
  unpaid: number;
  large_bookings: number;
};

export type Company = {
  id: string;
  name: string;
  phone: string;
  active: boolean;
};

export type AdminUser = {
  id: string;
  phone: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  role: string;
  status: string;
  phone_verified: boolean;
  company_id: string | null;
  created_at: string;
};

export type PassengerRow = {
  id: string;
  seat_id: string;
  first_name: string;
  last_name: string | null;
  phone: string | null;
};

export type LayoutCell = {
  id: string | null;
  row: number;
  column: number;
  cell_type: string;
  seat_id: string | null;
};

export type BusLayout = {
  id: string;
  bus_id: string;
  name: string;
  rows: number;
  columns: number;
  active: boolean;
  cells: LayoutCell[];
};

export type LayoutGenerateIn = {
  name: string;
  rows: number;
  columns: number;
  aisle_columns: number[];
  door_cells: [number, number][];
  full_width_rows: number[];
  women_rows: number[];
};

export type CityIn = {
  name: string;
  country: string;
  timezone: string;
  active: boolean;
};

export type RouteIn = {
  origin_city_id: string;
  destination_city_id: string;
  estimated_duration_minutes: number;
  distance_km: number;
  description?: string | null;
  active: boolean;
};

export type BusIn = {
  name: string;
  registration_number: string;
  model: string;
  seat_count: number;
  layout_type: string;
  active: boolean;
};

export type TripCreateIn = {
  route_id: string;
  bus_id: string;
  departure_datetime: string;
  base_price_minor: number;
  currency?: string;
  boarding_location?: string | null;
  destination_location?: string | null;
  status?: string;
};

export type TripPatchIn = {
  departure_datetime?: string;
  base_price_minor?: number;
  status?: string;
  boarding_location?: string;
  destination_location?: string;
};

export type MyReservation = Reservation & {
  trip: {
    departure_datetime: string;
    estimated_arrival_datetime: string;
    origin_city: string;
    destination_city: string;
    origin_timezone: string;
    destination_timezone: string;
    boarding_location: string | null;
  };
  tickets: { public_id: string; seat_number: string | null; status: string; passenger_name: string }[];
  can_cancel: boolean;
};

export type FaqLang = "uz" | "ru";

export type FaqItem = {
  id: string;
  lang: FaqLang;
  category: string;
  question: string;
  answer: string;
  position: number;
  active: boolean;
  updated_at: string;
};

export type FaqIn = Omit<FaqItem, "id" | "updated_at">;

export type AppConfig = {
  demo_mode: boolean;
  payment_methods: string[];
  bot_username: string | null;
  support_contact: string | null;
  support_chat: boolean;
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};
