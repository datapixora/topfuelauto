"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getToken, clearToken, setToken as storeToken } from "../../lib/auth";
import { apiGet } from "../../lib/api";

type AuthUser = {
  id: number;
  email: string;
  is_admin?: boolean;
  is_active?: boolean;
  plan_name?: string | null;
};

type AuthContextType = {
  user: AuthUser | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => void;
  setToken: (token: string) => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const me = await apiGet<AuthUser>("/auth/me");
      setUser(me);
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const handler = () => void refresh();
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, [refresh]);

  const logout = () => {
    clearToken();
    setUser(null);
    setLoading(false);
  };

  const setTokenAndRefresh = (token: string) => {
    storeToken(token);
    void refresh();
  };

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout, setToken: setTokenAndRefresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
