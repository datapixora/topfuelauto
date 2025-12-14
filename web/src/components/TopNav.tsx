"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import LoginDialog from "./auth/LoginDialog";
import { Button } from "./ui/button";
import { useAuth } from "./auth/AuthProvider";
import { listNotifications, markAllNotificationsRead, markNotificationRead } from "../lib/api";
import { NotificationItem } from "../lib/types";

export default function TopNav() {
  const router = useRouter();
  const { user, loading, logout, refresh } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [notifLoading, setNotifLoading] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const notifRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  const loadNotifications = async () => {
    if (!user) return;
    setNotifLoading(true);
    try {
      const res = await listNotifications(10);
      setNotifications(res.notifications || []);
      setUnread(res.unread_count || 0);
    } catch (err) {
      // silent fail for nav
    } finally {
      setNotifLoading(false);
    }
  };

  useEffect(() => {
    if (!user) {
      setNotifications([]);
      setUnread(0);
      setNotifOpen(false);
      return;
    }
    void loadNotifications();
    const interval = setInterval(() => void loadNotifications(), 60000);
    return () => clearInterval(interval);
  }, [user]);

  const handleNotificationClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await markNotificationRead(notif.id);
        await loadNotifications();
      } catch {
        /* ignore */
      }
    }
    setNotifOpen(false);
    if (notif.link_url) {
      router.push(notif.link_url);
    }
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
          <>
            <div className="relative" ref={notifRef}>
              <Button
                variant="ghost"
                className="relative border border-slate-700"
                onClick={() => {
                  setNotifOpen((o) => !o);
                  setMenuOpen(false);
                  void loadNotifications();
                }}
              >
                <span className="mr-1">🔔</span>
                {notifLoading ? (
                  <span className="text-xs text-slate-400">...</span>
                ) : (
                  <span className="text-xs text-slate-300">{unread || 0}</span>
                )}
                {unread > 0 && (
                  <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-emerald-400 shadow" />
                )}
              </Button>
              {notifOpen && (
                <div className="absolute right-0 mt-2 w-80 rounded-md border border-slate-800 bg-slate-900 shadow-lg z-30">
                  <div className="flex items-center justify-between px-3 py-2 text-xs text-slate-400">
                    <span>Notifications</span>
                    <button
                      className="underline text-emerald-300"
                      onClick={async () => {
                        await markAllNotificationsRead();
                        await loadNotifications();
                      }}
                    >
                      Mark all read
                    </button>
                  </div>
                  <div className="max-h-80 overflow-auto">
                    {notifications.length === 0 && (
                      <div className="px-3 py-4 text-sm text-slate-400">No notifications yet.</div>
                    )}
                    {notifications.map((n) => (
                      <button
                        key={n.id}
                        className={`block w-full px-3 py-2 text-left text-sm hover:bg-slate-800 ${
                          n.is_read ? "text-slate-300" : "text-emerald-100"
                        }`}
                        onClick={() => handleNotificationClick(n)}
                      >
                        <div className="font-semibold">{n.title}</div>
                        {n.body && <div className="text-xs text-slate-400">{n.body}</div>}
                        {n.created_at && (
                          <div className="text-[11px] text-slate-500">
                            {new Date(n.created_at).toLocaleString()}
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
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
                  <Link
                    className="block px-3 py-2 text-sm hover:bg-slate-800"
                    href="/account/alerts"
                    onClick={() => setMenuOpen(false)}
                  >
                    Alerts
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
          </>
        )}
      </div>
    </nav>
  );
}
