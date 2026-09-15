import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { bookingApi } from "../api/booking";
import { rememberBookingPhone } from "../api/client";
import { Button, ErrorBox, Field, Input, followSpot } from "../components/Ui";
import { formatPhoneDisplay, phoneToApi } from "../utils/format";

export function LookupPage() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const mutation = useMutation({
    mutationFn: () => bookingApi.lookup(phoneToApi(phone), code.trim().toUpperCase()),
    onSuccess: (reservation) => {
      rememberBookingPhone(phoneToApi(phone));
      navigate(`/success/${reservation.public_code}`, { viewTransition: true });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.02em] text-ink sm:text-[34px]">
          Bronni topish
        </h1>
        <p className="text-[15px] leading-relaxed text-muted">
          Chipta olishda ko‘rsatgan raqamingizni va tasdiqdagi kodni kiriting.
        </p>
      </header>

      {mutation.isError && <ErrorBox error={mutation.error} />}

      <form
        onSubmit={onSubmit}
        onPointerMove={followSpot}
        className="glass spot flex flex-col gap-5 rounded-plate p-5"
      >
        <Field label="Telefon" htmlFor="lookup-phone">
          <Input
            id="lookup-phone"
            name="phone"
            value={phone}
            onChange={(e) => setPhone(formatPhoneDisplay(e.target.value))}
            placeholder="+998 90 123 45 67"
            inputMode="tel"
            autoComplete="tel"
            className="tnum"
            required
          />
        </Field>
        <Field label="Bron kodi" hint="Chekdagi kod, masalan TSH-8F2KQ." htmlFor="lookup-code">
          <Input
            id="lookup-code"
            name="code"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="TSH-8F2KQ"
            autoCapitalize="characters"
            autoComplete="off"
            className="tnum tracking-[0.14em]"
            required
          />
        </Field>
        <Button
          type="submit"
          size="lg"
          block
          loading={mutation.isPending}
          icon={mutation.isPending ? undefined : <MagnifyingGlass size={18} weight="bold" />}
        >
          Topish
        </Button>
      </form>
    </div>
  );
}
