"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import LoginDialog from "./auth/LoginDialog";
import { Button } from "./ui/button";
import { useAuth } from "./auth/AuthProvider";

export default function TopNav() {
  const router = useRouter();
  const { user, loading, logout, refresh } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  const goDashboard = () => {
    router.push("/account");
  };

  return (
    <nav className="flex items-center justify-between py-4">
      <Link href="/" className="text-xl font-semibold tracking-tight text-slate-50">
        TopFuelAuto
      </Link>
      <div className="flex items-center gap-2">
        {!user && !loading && (
          <>
            <Button onClick={() => router.push("/search")}>Start searching</Button>
            <Button variant="ghost" className="border border-slate-700" onClick={() => router.push("/pricing")}>
              Pricing
            </Button>
            <LoginDialog
              onLoggedIn={() => {
                void refresh();
                router.push("/account");
              }}
              triggerVariant="ghost"
              label="Sign in"
            />
          </>
        )}
        {user && (
          <div className="relative" ref={menuRef}>
            <Button variant="ghost" className="border border-slate-700" onClick={() => setMenuOpen((o) => !o)}>
              {user.email?.split("@")[0] || "Account"}
            </Button>
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-48 rounded-md border border-slate-800 bg-slate-900 shadow-lg z-20">
                <Link
                  className="block px-3 py-2 text-sm hover:bg-slate-800"
                  href="/account"
                  onClick={() => setMenuOpen(false)}
                >
                  Dashboard
                </Link>
                <Link
                  className="block px-3 py-2 text-sm hover:bg-slate-800"
                  href="/search"
                  onClick={() => setMenuOpen(false)}
                >
                  Search
                </Link>
                <Link
                  className="block px-3 py-2 text-sm hover:bg-slate-800"
                  href="/account/assist"
                  onClick={() => setMenuOpen(false)}
                >
                  Assist
                </Link>
                <button
                  className="block w-full text-left px-3 py-2 text-sm hover:bg-slate-800"
                  onClick={() => {
                    setMenuOpen(false);
                    logout();
                    router.replace("/");
                    router.refresh();
                  }}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
