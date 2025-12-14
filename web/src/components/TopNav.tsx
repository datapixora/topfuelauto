"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "../lib/auth";
import LoginDialog from "./auth/LoginDialog";
import { Button } from "./ui/button";

export default function TopNav() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(getToken());
    const handler = () => setToken(getToken());
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const onSignOut = () => {
    clearToken();
    setToken(null);
    router.replace("/");
    router.refresh();
  };

  return (
    <nav className="flex items-center justify-between py-4">
      <Link href="/" className="text-xl font-semibold tracking-tight text-slate-50">
        TopFuelAuto
      </Link>
      <div className="flex items-center gap-3">
        <Link href="/pricing" className="text-sm text-slate-300 hover:text-white transition">
          Pricing
        </Link>
        <Link href="/dashboard" className="text-sm text-slate-300 hover:text-white transition">
          Dashboard
        </Link>
        {token ? (
          <Button variant="ghost" className="border border-slate-700" onClick={onSignOut}>
            Sign out
          </Button>
        ) : (
          <LoginDialog onLoggedIn={(val) => setToken(val)} triggerVariant="ghost" />
        )}
      </div>
    </nav>
  );
}
