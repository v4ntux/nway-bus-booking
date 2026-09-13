import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "@phosphor-icons/react";
import { authApi } from "../../api/admin";
import { setTokens } from "../../api/client";
import { BrandWord } from "../../components/BrandMark";
import { Atmosphere } from "../../components/PassengerLayout";
import { Button, ErrorBox, Field, Input, backLinkClass, followSpot } from "../../components/Ui";
import { ThemeToggle } from "../../components/ThemeToggle";

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const tokens = await authApi.adminLogin(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      navigate("/admin");
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="relative flex min-h-[100dvh] flex-col">
      <Atmosphere />
      <div className="page-stage flex min-h-[100dvh] flex-col">
        <header className="flex h-16 items-center justify-between px-4">
          <Link to="/" className={backLinkClass}>
            <ArrowLeft size={15} weight="bold" />
            Saytga
          </Link>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 items-center justify-center px-4 pb-20">
          <div className="page-enter w-full max-w-sm">
            <div className="mb-7 flex flex-col gap-2">
              <BrandWord />
              <h1 className="text-[26px] font-semibold leading-tight tracking-[-0.02em] text-ink">
                Xodimlar uchun kirish
              </h1>
            </div>

            {error != null && (
              <div className="mb-4">
                <ErrorBox error={error} />
              </div>
            )}

            <form onSubmit={onSubmit} onPointerMove={followSpot} className="glass spot flex flex-col gap-5 rounded-plate p-5">
              <Field label="Email" htmlFor="admin-email">
                <Input
                  name="email"
                  id="admin-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  required
                />
              </Field>
              <Field label="Parol" htmlFor="admin-password">
                <Input
                  name="password"
                  id="admin-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </Field>
              <Button type="submit" size="lg" block loading={pending}>
                Kirish
              </Button>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
}
