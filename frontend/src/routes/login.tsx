import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { setToken } from "@/lib/api";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [{ title: "CodeLens — Login" }],
  }),
  component: LoginPage,
});

function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const endpoint = isLogin ? "/api/v1/auth/login" : "/api/v1/auth/register";

      const options: RequestInit = {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      };

      if (isLogin) {
        options.body = JSON.stringify({ email, password });
      } else {
        const username = email.split("@")[0];
        options.body = JSON.stringify({ email, password, username });
      }

      const res = await fetch(endpoint, options);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.message || "Authentication failed");
      }

      if (isLogin) {
        setToken(data.access_token);
        toast.success("Logged in!");
        navigate({ to: "/" });
      } else {
        toast.success("Account created! Please log in.");
        setIsLogin(true);
      }
    } catch (e) {
      console.error("Auth error:", e);
      toast.error(e instanceof Error ? e.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <Link to="/" className="inline-flex items-baseline gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-foreground font-mono text-[11px] font-medium text-background">
              C
            </div>
            <span className="font-display text-3xl">CodeLens</span>
          </Link>
        </div>

        <div
          className="rounded-md border border-border bg-card p-8"
          style={{ boxShadow: "var(--shadow-paper)" }}
        >
          <h1 className="mb-6 font-display text-3xl">
            {isLogin ? "Welcome back" : "Create account"}
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full rounded-sm border border-border bg-background px-4 py-3 font-mono text-[13px] text-foreground outline-none focus:border-accent focus:ring-1 focus:ring-accent"
                placeholder="you@email.com"
              />
            </div>
            <div>
              <label className="mb-1 block font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-sm border border-border bg-background px-4 py-3 font-mono text-[13px] text-foreground outline-none focus:border-accent focus:ring-1 focus:ring-accent"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-sm bg-foreground py-3 font-mono text-[11px] uppercase tracking-[0.25em] text-background transition-all hover:bg-accent disabled:opacity-50"
            >
              {busy ? "please wait…" : isLogin ? "Log in" : "Sign up"}
            </button>
          </form>

          <p className="mt-6 text-center font-mono text-[11px] text-muted-foreground">
            {isLogin ? "Need an account? " : "Already have an account? "}
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-accent underline underline-offset-4 hover:text-foreground"
            >
              {isLogin ? "Sign up" : "Log in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
