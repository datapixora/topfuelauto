"use client";

import { useState } from "react";
import { login, signup } from "../../lib/api";
import { setToken, clearToken, getToken } from "../../lib/auth";

export default function AccountPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const action = mode === "login" ? login : signup;
      const res = await action(email, password);
      setToken(res.access_token);
      setStatus("Authenticated. Token stored locally (MVP).");
    } catch (err) {
      setStatus("Failed");
    }
  };

  return (
    <div className="card max-w-md">
      <div className="flex items-center gap-4 mb-4">
        <button
          className={`px-3 py-2 rounded ${mode === "login" ? "bg-brand-accent text-slate-950" : "bg-slate-800"}`}
          onClick={() => setMode("login")}
        >
          Login
        </button>
        <button
          className={`px-3 py-2 rounded ${mode === "signup" ? "bg-brand-accent text-slate-950" : "bg-slate-800"}`}
          onClick={() => setMode("signup")}
        >
          Signup
        </button>
      </div>
      <form className="space-y-3" onSubmit={onSubmit}>
        <input
          className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit" className="w-full bg-brand-accent text-slate-950 font-semibold rounded px-3 py-2">
          {mode === "login" ? "Login" : "Create account"}
        </button>
      </form>
      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <div>{status}</div>
        {getToken() && (
          <button onClick={clearToken} className="text-brand-accent">Logout</button>
        )}
      </div>
      <p className="text-xs text-slate-500 mt-4">Token is stored in localStorage for MVP. Use HTTPS in production.</p>
    </div>
  );
}