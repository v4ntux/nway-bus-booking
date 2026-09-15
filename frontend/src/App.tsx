import { Navigate, Route, Routes } from "react-router-dom";
import { PassengerLayout } from "./components/PassengerLayout";
import { AdminLayout } from "./components/AdminLayout";
import { HomePage } from "./pages/HomePage";
import { ResultsPage } from "./pages/ResultsPage";
import { SeatsPage } from "./pages/SeatsPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { PaymentPage } from "./pages/PaymentPage";
import { SuccessPage } from "./pages/SuccessPage";
import { TicketPage } from "./pages/TicketPage";
import { LookupPage } from "./pages/LookupPage";
import { MyTicketsPage } from "./pages/MyTicketsPage";
import { HelpPage } from "./pages/HelpPage";
import { AdminLoginPage } from "./pages/admin/AdminLoginPage";
import { DashboardPage } from "./pages/admin/DashboardPage";
import { CitiesPage } from "./pages/admin/CitiesPage";
import { RoutesPage } from "./pages/admin/RoutesPage";
import { BusesPage } from "./pages/admin/BusesPage";
import { LayoutPage } from "./pages/admin/LayoutPage";
import { TripsPage } from "./pages/admin/TripsPage";
import { ReservationsPage } from "./pages/admin/ReservationsPage";
import { PassengersPage } from "./pages/admin/PassengersPage";
import { PaymentsPage } from "./pages/admin/PaymentsPage";
import { UsersPage } from "./pages/admin/UsersPage";
import { CompaniesPage } from "./pages/admin/CompaniesPage";
import { FaqPage } from "./pages/admin/FaqPage";

export default function App() {
  return (
    <Routes>
      <Route element={<PassengerLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/book" element={<HomePage />} />
        <Route path="/trips" element={<ResultsPage />} />
        <Route path="/trips/:tripId/seats" element={<SeatsPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/pay/:code" element={<PaymentPage />} />
        <Route path="/success/:code" element={<SuccessPage />} />
        <Route path="/ticket/:publicId" element={<TicketPage />} />
        <Route path="/lookup" element={<LookupPage />} />
        <Route path="/my" element={<MyTicketsPage />} />
        <Route path="/faq" element={<HelpPage />} />
        <Route path="/support" element={<HelpPage />} />
      </Route>
      <Route path="/login" element={<AdminLoginPage />} />
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="cities" element={<CitiesPage />} />
        <Route path="routes" element={<RoutesPage />} />
        <Route path="buses" element={<BusesPage />} />
        <Route path="buses/:busId/layout" element={<LayoutPage />} />
        <Route path="trips" element={<TripsPage />} />
        <Route path="reservations" element={<ReservationsPage />} />
        <Route path="passengers" element={<PassengersPage />} />
        <Route path="payments" element={<PaymentsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="companies" element={<CompaniesPage />} />
        <Route path="faq" element={<FaqPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
