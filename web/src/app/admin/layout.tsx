import Link from "next/link";
import { ReactNode } from "react";
import { cn } from "../../lib/utils";

const links = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/plans", label: "Plans" },
  { href: "/admin/subscriptions", label: "Subscriptions" },
  { href: "/admin/search-analytics", label: "Search Analytics" },
  { href: "/admin/providers", label: "Providers" },
  { href: "/admin/proxies", label: "Proxies" },
  { href: "/admin/data/sources", label: "Data Engine" },
  { href: "/admin/imports", label: "Imports" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen grid md:grid-cols-[240px_1fr] bg-slate-950 text-slate-100">
      <aside className="border-r border-slate-800 p-4 space-y-4 bg-slate-900/60">
        <div className="text-xl font-bold">TopFuel Admin</div>
        <nav className="space-y-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "block px-3 py-2 rounded-md text-sm hover:bg-slate-800 transition",
                link.href === "/admin" ? "font-semibold" : ""
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="p-6 space-y-4">
        <header className="flex justify-between items-center">
          <div>
            <div className="text-2xl font-semibold">Admin Console</div>
            <div className="text-sm text-slate-400">Operational metrics and controls</div>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
