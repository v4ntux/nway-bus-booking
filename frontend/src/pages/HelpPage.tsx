import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import WebApp from "@twa-dev/sdk";
import { CaretDown, ChatCircleText, MagnifyingGlass } from "@phosphor-icons/react";
import { supportApi } from "../api/support";
import { Button, EmptyState, ErrorBox, Input, PageTitle, Skeleton } from "../components/Ui";
import { useTelegram } from "../telegram/TelegramProvider";
import type { FaqLang } from "../types/api";

const LANGS: { value: FaqLang; label: string }[] = [
  { value: "uz", label: "O‘zbekcha" },
  { value: "ru", label: "Русский" },
];

function SupportCard() {
  const { isTelegram } = useTelegram();
  const config = useQuery({ queryKey: ["app-config"], queryFn: supportApi.appConfig, staleTime: 60_000 });
  const bot = config.data?.bot_username;
  const link = bot ? `https://t.me/${bot}?start=support` : null;
  const contact = config.data?.support_contact;

  function openChat() {
    if (!link) return;
    if (isTelegram) {
      WebApp.openTelegramLink(link);
      WebApp.close();
    } else {
      window.open(link, "_blank", "noopener");
    }
  }

  return (
    <section id="support" className="glass flex flex-col gap-3 rounded-plate p-5">
      <div className="flex items-center gap-3">
        <span className="well flex h-11 w-11 shrink-0 items-center justify-center rounded-panel text-accent-strong">
          <ChatCircleText size={22} weight="duotone" />
        </span>
        <div>
          <h2 className="text-[17px] font-semibold text-ink">Javob topilmadimi?</h2>
          <p className="text-[14px] text-muted">Operatorga yozing — javob Telegram chatiga keladi.</p>
        </div>
      </div>
      {link && config.data?.support_chat && (
        <Button size="lg" block onClick={openChat}>
          💬 Operatorga yozish
        </Button>
      )}
      {contact && <p className="text-[14px] text-ink">📞 {contact}</p>}
      {config.isSuccess && !contact && !(link && config.data.support_chat) && (
        <p className="text-[14px] text-muted">Onlayn yordam hozircha ulanmagan.</p>
      )}
    </section>
  );
}

export function HelpPage() {
  const { user } = useTelegram();
  const { pathname } = useLocation();
  const supportRef = useRef<HTMLDivElement>(null);
  const [lang, setLang] = useState<FaqLang>(() => (user?.language_code?.startsWith("ru") ? "ru" : "uz"));
  const [search, setSearch] = useState("");
  const query = useQuery({ queryKey: ["faq", lang], queryFn: () => supportApi.faq(lang), staleTime: 5 * 60_000 });

  useEffect(() => {
    if (pathname === "/support") supportRef.current?.scrollIntoView({ block: "start" });
  }, [pathname, query.isSuccess]);

  const items = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const all = query.data ?? [];
    return needle ? all.filter((f) => `${f.question} ${f.answer}`.toLowerCase().includes(needle)) : all;
  }, [query.data, search]);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <PageTitle sub="Chipta, to‘lov va safar haqida ko‘p so‘raladigan savollar">Yordam markazi</PageTitle>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <MagnifyingGlass size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" aria-hidden="true" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={lang === "ru" ? "Поиск по вопросам" : "Savollardan qidirish"}
            aria-label="Qidirish"
            className="pl-10"
          />
        </div>
        <div role="group" aria-label="Til" className="well flex h-12 shrink-0 gap-1 rounded-control p-1">
          {LANGS.map((l) => (
            <button
              key={l.value}
              type="button"
              aria-pressed={lang === l.value}
              onClick={() => setLang(l.value)}
              className={`rounded-[10px] px-3 text-[14px] font-semibold transition-colors duration-200 ${
                lang === l.value ? "btn-sun shadow-none" : "text-muted hover:text-ink"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {query.isLoading && (
        <div className="flex flex-col gap-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}
      {query.isError && <ErrorBox error={query.error} />}
      {query.isSuccess && items.length === 0 && (
        <EmptyState title={search ? "Hech narsa topilmadi" : "Savollar hali qo‘shilmagan"} body="Operatorga yozing — yordam beramiz." />
      )}

      {items.length > 0 && (
        <ul className="flex flex-col gap-2">
          {items.map((f) => (
            <li key={f.id}>
              <details className="glass group rounded-panel">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3.5 text-[15.5px] font-medium text-ink">
                  {f.question}
                  <CaretDown size={16} weight="bold" className="shrink-0 text-muted transition-transform duration-200 group-open:rotate-180" />
                </summary>
                <p className="whitespace-pre-line px-4 pb-4 text-[15px] leading-relaxed text-muted">{f.answer}</p>
              </details>
            </li>
          ))}
        </ul>
      )}

      <div ref={supportRef} className="scroll-mt-24">
        <SupportCard />
      </div>
    </div>
  );
}
