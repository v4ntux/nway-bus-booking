import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import WebApp from "@twa-dev/sdk";

type TelegramUser = {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
};

type TelegramContextValue = {
  isTelegram: boolean;
  user: TelegramUser | null;
  colorScheme: "light" | "dark";
  platform: string;
  initData: string;
  close: () => void;
  haptic: (type?: "light" | "medium" | "heavy" | "success" | "error") => void;
};

const TelegramContext = createContext<TelegramContextValue>({
  isTelegram: false,
  user: null,
  colorScheme: "light",
  platform: "unknown",
  initData: "",
  close: () => {},
  haptic: () => {},
});

function detectTelegram(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(window.Telegram?.WebApp?.initData);
}

function hexToRgbTriplet(hex: string): string | null {
  const raw = hex.replace("#", "").trim();
  if (raw.length !== 6) return null;
  const r = parseInt(raw.slice(0, 2), 16);
  const g = parseInt(raw.slice(2, 4), 16);
  const b = parseInt(raw.slice(4, 6), 16);
  if ([r, g, b].some(Number.isNaN)) return null;
  return `${r} ${g} ${b}`;
}

function applyTelegramTheme() {
  const tp = WebApp.themeParams;
  const root = document.documentElement;

  const bgRgb = tp.bg_color ? hexToRgbTriplet(tp.bg_color) : null;
  const textRgb = tp.text_color ? hexToRgbTriplet(tp.text_color) : null;
  const secondaryRgb = tp.secondary_bg_color ? hexToRgbTriplet(tp.secondary_bg_color) : null;

  if (bgRgb) {
    root.style.setProperty("--c-paper", bgRgb);
    root.style.setProperty("--tg-bg", tp.bg_color!);
  }
  if (textRgb) root.style.setProperty("--c-ink", textRgb);
  if (secondaryRgb) {
    root.style.setProperty("--c-glass", secondaryRgb);
    root.style.setProperty("--c-surface", secondaryRgb);
  }
  if (tp.button_color) root.style.setProperty("--tg-button", tp.button_color);
  if (tp.button_text_color) root.style.setProperty("--tg-button-text", tp.button_text_color);

  root.dataset.telegram = "true";
  root.dataset.theme = WebApp.colorScheme;
}

export function TelegramProvider({ children }: { children: ReactNode }) {
  const [isTelegram] = useState(detectTelegram);
  const [colorScheme, setColorScheme] = useState<"light" | "dark">(
    () => (isTelegram ? WebApp.colorScheme : "light") as "light" | "dark",
  );

  useEffect(() => {
    if (!isTelegram) return;

    WebApp.ready();
    WebApp.expand();
    WebApp.enableClosingConfirmation();
    applyTelegramTheme();
    setColorScheme(WebApp.colorScheme as "light" | "dark");

    const onTheme = () => {
      applyTelegramTheme();
      setColorScheme(WebApp.colorScheme as "light" | "dark");
    };

    WebApp.onEvent("themeChanged", onTheme);
    return () => WebApp.offEvent("themeChanged", onTheme);
  }, [isTelegram]);

  const value = useMemo<TelegramContextValue>(() => {
    const user = isTelegram && WebApp.initDataUnsafe.user
      ? {
          id: WebApp.initDataUnsafe.user.id,
          first_name: WebApp.initDataUnsafe.user.first_name,
          last_name: WebApp.initDataUnsafe.user.last_name,
          username: WebApp.initDataUnsafe.user.username,
          language_code: WebApp.initDataUnsafe.user.language_code,
        }
      : null;

    return {
      isTelegram,
      user,
      colorScheme,
      platform: isTelegram ? WebApp.platform : "web",
      initData: isTelegram ? WebApp.initData : "",
      close: () => WebApp.close(),
      haptic: (type = "light") => {
        if (type === "success" || type === "error") {
          WebApp.HapticFeedback.notificationOccurred(type);
        } else {
          WebApp.HapticFeedback.impactOccurred(type);
        }
      },
    };
  }, [isTelegram, colorScheme]);

  return <TelegramContext.Provider value={value}>{children}</TelegramContext.Provider>;
}

export function useTelegram() {
  return useContext(TelegramContext);
}

/** Uzbekistan-style phone from Telegram user id is unavailable; use username hint only. */
export function telegramDisplayName(user: TelegramUser | null): string | undefined {
  if (!user) return undefined;
  return [user.first_name, user.last_name].filter(Boolean).join(" ").trim() || user.username;
}
