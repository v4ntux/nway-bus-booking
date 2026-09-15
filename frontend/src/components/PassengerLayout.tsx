import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import WebApp from "@twa-dev/sdk";
import { Link, Outlet, useLocation, useMatch, useNavigate } from "react-router-dom";
import { MagnifyingGlass, Question, Ticket, X } from "@phosphor-icons/react";
import { supportApi } from "../api/support";
import { BrandMark } from "./BrandMark";
import { Stepper } from "./Stepper";
import { ThemeToggle } from "./ThemeToggle";
import { useTelegram } from "../telegram/TelegramProvider";
import { startParamPath } from "../telegram/startParam";

const headerLinkClass =
  "glass inline-flex h-11 items-center gap-2 rounded-control px-3.5 text-[14px] font-medium text-ink no-underline transition-all duration-300 ease-out hover:-translate-y-0.5 hover:border-accent/40";

/** A t.me/<bot>?startapp=… link lands once per Mini App session, not on every reload. */
function useStartParamRedirect(isTelegram: boolean) {
  const navigate = useNavigate();
  useEffect(() => {
    if (!isTelegram) return;
    const target = startParamPath(WebApp.initDataUnsafe.start_param);
    if (!target) return;
    try {
      if (sessionStorage.getItem("nway_start_param_done")) return;
      sessionStorage.setItem("nway_start_param_done", "1");
    } catch {
      /* storage blocked: redirect anyway */
    }
    navigate(target, { replace: true });
  }, [isTelegram, navigate]);
}

function useBookingStep(): 0 | 1 | 2 | 3 | null {
  const { pathname } = useLocation();
  const seats = useMatch("/trips/:tripId/seats");
  if (pathname === "/trips") return 0;
  if (seats) return 1;
  if (pathname === "/checkout") return 2;
  if (pathname.startsWith("/pay/")) return 3;
  return null;
}

export function Atmosphere() {
  return (
    <>
      <div className="ambient" aria-hidden="true">
        <div className="ambient-halo" />
        <div className="ambient-lamp ambient-lamp-sun" />
        <div className="ambient-lamp ambient-lamp-sky" />
        <div className="ambient-lamp ambient-lamp-rose" />
      </div>
      <div className="grain" aria-hidden="true" />
    </>
  );
}

export function PassengerLayout() {
  const step = useBookingStep();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const config = useQuery({ queryKey: ["app-config"], queryFn: supportApi.appConfig, staleTime: 60_000 });
  const { isTelegram, user, close } = useTelegram();
  useStartParamRedirect(isTelegram);

  useEffect(() => {
    if (!isTelegram) return;
    const goBack = () => {
      if (window.history.state?.idx > 0) navigate(-1);
      else navigate("/");
    };
    if (pathname === "/" || pathname === "/book") WebApp.BackButton.hide();
    else WebApp.BackButton.show();
    WebApp.BackButton.onClick(goBack);
    window.scrollTo(0, 0);
    return () => { WebApp.BackButton.offClick(goBack); WebApp.BackButton.hide(); };
  }, [isTelegram, pathname, navigate]);

  return (
    <div className="relative flex min-h-[100dvh] flex-col">
      {!isTelegram && (
        <a href="#main" className="skip-link">
          Kontentga o‘tish
        </a>
      )}

      <Atmosphere />

      <div className="page-stage flex min-h-[100dvh] flex-col">
        <header className="sticky top-0 z-30">
          <div className="glass-bar">
            <div className="mx-auto flex h-14 max-w-4xl items-center justify-between gap-3 px-4 sm:h-16">
              <BrandMark size={isTelegram ? "sm" : "md"} />
              <div className="flex items-center gap-2">
                {isTelegram && user && (
                  <span className="glass hidden rounded-full px-3 py-1.5 text-[13px] font-medium text-muted sm:inline">
                    Salom, {user.first_name}
                  </span>
                )}
                {isTelegram ? (
                  <Link to="/my" aria-label="Chiptalarim" viewTransition className={headerLinkClass}>
                    <Ticket size={16} weight="bold" />
                    <span className="hidden sm:inline">Chiptalarim</span>
                  </Link>
                ) : (
                  <Link to="/lookup" aria-label="Chiptani topish" viewTransition className={headerLinkClass}>
                    <MagnifyingGlass size={16} weight="bold" />
                    <span className="hidden sm:inline">Chiptani topish</span>
                  </Link>
                )}
                <Link to="/faq" aria-label="Yordam" viewTransition className={headerLinkClass}>
                  <Question size={16} weight="bold" />
                  <span className="hidden sm:inline">Yordam</span>
                </Link>
                {isTelegram ? (
                  <button
                    type="button"
                    onClick={close}
                    aria-label="Yopish"
                    className="glass flex h-11 w-11 items-center justify-center rounded-full text-muted transition-all duration-300 hover:text-ink"
                  >
                    <X size={18} weight="bold" />
                  </button>
                ) : (
                  <ThemeToggle />
                )}
              </div>
            </div>

            {step !== null && (
              <div className="border-t border-hairline/70">
                <div className="mx-auto max-w-4xl px-4 py-3">
                  <Stepper current={step} />
                </div>
              </div>
            )}
          </div>
        </header>

        <main id="main" className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 sm:py-10">
          {config.data?.demo_mode && <div role="note" className="mb-5 rounded-panel border border-accent/30 bg-accent-soft px-4 py-3 text-sm leading-relaxed text-accent-strong">
            🧪 <strong>Sinov rejimi.</strong> Reyslar namuna uchun. Pul yechilmaydi, chipta haqiqiy safar uchun yaroqsiz.
          </div>}
          <Outlet />
        </main>

        {!isTelegram && (
          <footer className="mt-8 border-t border-hairline/70">
            <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-[13px] text-muted">
              <p>🚌 Shaharlararo avtobuslar. 💵 To‘lov avtobusga chiqishda.</p>
              <div className="flex items-center gap-4">
                <Link
                  to="/lookup"
                  aria-label="Chiptani topish"
                  viewTransition
                  className="text-ink no-underline underline-offset-4 transition-opacity duration-200 hover:opacity-70 hover:underline"
                >
                  Bronni tekshirish
                </Link>
                <Link
                  to="/faq"
                  viewTransition
                  className="text-ink no-underline underline-offset-4 transition-opacity duration-200 hover:opacity-70 hover:underline"
                >
                  Yordam
                </Link>
                <Link
                  to="/login"
                  className="no-underline underline-offset-4 transition-colors duration-200 hover:text-ink hover:underline"
                >
                  Xodimlar uchun
                </Link>
              </div>
            </div>
          </footer>
        )}

        {isTelegram && <div className="tg-safe-bottom" aria-hidden="true" />}
      </div>
    </div>
  );
}
