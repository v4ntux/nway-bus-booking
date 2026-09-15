import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Armchair,
  Buildings,
  Bus,
  CreditCard,
  Gauge,
  List,
  MapPin,
  Path,
  Question,
  SignOut,
  Ticket,
  UserCircle,
  UsersThree,
  X,
} from "@phosphor-icons/react";
import { clearTokens } from "../api/client";
import { BrandWord } from "./BrandMark";
import { Atmosphere } from "./PassengerLayout";
import { ThemeToggle } from "./ThemeToggle";

const GROUPS: { title: string; links: { to: string; label: string; icon: typeof Gauge }[] }[] = [
  {
    title: "Bugun",
    links: [
      { to: "", label: "Umumiy holat", icon: Gauge },
      { to: "reservations", label: "Bronlar", icon: Ticket },
      { to: "payments", label: "To‘lovlar", icon: CreditCard },
      { to: "passengers", label: "Yo‘lovchilar", icon: UsersThree },
    ],
  },
  {
    title: "Jadval",
    links: [
      { to: "trips", label: "Reyslar", icon: Bus },
      { to: "routes", label: "Yo‘nalishlar", icon: Path },
      { to: "cities", label: "Shaharlar", icon: MapPin },
      { to: "buses", label: "Avtobuslar", icon: Armchair },
    ],
  },
  {
    title: "Tizim",
    links: [
      { to: "users", label: "Foydalanuvchilar", icon: UserCircle },
      { to: "companies", label: "Kompaniyalar", icon: Buildings },
      { to: "faq", label: "Savollar (FAQ)", icon: Question },
    ],
  },
];

export function AdminLayout() {
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("nway_access_token")) navigate("/login");
  }, [navigate]);

  function signOut() {
    clearTokens();
    navigate("/login");
  }

  return (
    <div className="relative min-h-[100dvh]">
      <Atmosphere />
      <div className="page-stage min-h-[100dvh] lg:grid lg:grid-cols-[248px_1fr]">
        <div className="glass-bar sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-hairline/80 px-4 lg:hidden">
          <button
            type="button"
            onClick={() => setNavOpen((o) => !o)}
            aria-label="Menyu"
            aria-expanded={navOpen}
            className="glass inline-flex h-10 w-10 items-center justify-center rounded-control text-ink"
          >
            {navOpen ? <X size={18} weight="bold" /> : <List size={18} weight="bold" />}
          </button>
          <BrandWord size="sm" />
          <ThemeToggle />
        </div>

        <aside
          className={`glass-bar border-r border-hairline/80 lg:sticky lg:top-0 lg:block lg:h-[100dvh] ${
            navOpen ? "block" : "hidden"
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="hidden h-16 items-center justify-between gap-2 px-5 lg:flex">
              <BrandWord size="sm" />
              <span className="rounded-full border border-line/80 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-faint">
                admin
              </span>
            </div>

            <nav className="flex flex-1 flex-col gap-5 overflow-y-auto p-3">
              {GROUPS.map((group) => (
                <div key={group.title} className="flex flex-col gap-0.5">
                  <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-faint">
                    {group.title}
                  </p>
                  {group.links.map(({ to, label, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to === "" ? "/admin" : `/admin/${to}`}
                      end={to === ""}
                      onClick={() => setNavOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-3 rounded-control px-3 py-2.5 text-[14px] font-medium no-underline transition-all duration-200 ${
                          isActive
                            ? "btn-sun shadow-none"
                            : "text-muted hover:bg-surface/60 hover:text-ink"
                        }`
                      }
                    >
                      <Icon size={17} weight="regular" className="shrink-0" />
                      {label}
                    </NavLink>
                  ))}
                </div>
              ))}
            </nav>

            <div className="flex items-center gap-2 border-t border-hairline/80 p-3">
              <button
                type="button"
                onClick={signOut}
                className="flex flex-1 items-center gap-2.5 rounded-control px-3 py-2.5 text-[14px] font-medium text-muted transition-colors duration-200 hover:bg-surface/60 hover:text-ink"
              >
                <SignOut size={17} weight="regular" />
                Chiqish
              </button>
              <span className="hidden lg:block">
                <ThemeToggle />
              </span>
            </div>
          </div>
        </aside>

        <main className="min-w-0 px-4 py-6 sm:px-6 lg:py-8">
          <div className="page-enter mx-auto flex max-w-6xl flex-col gap-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
