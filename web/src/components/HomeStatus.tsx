"use client";

import { useEffect, useMemo, useState } from "react";

type PingState = { status: "idle" | "loading" | "ok" | "error"; message?: string };

export default function HomeStatus() {
  const [state, setState] = useState<PingState>({ status: "idle" });
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;

  const healthUrl = useMemo(() => {
    if (!apiBase) return null;
    const trimmed = apiBase.replace(/\/+$/, "");
    if (trimmed.endsWith("/api/v1")) return `${trimmed}/health`;
    return `${trimmed}/api/v1/health`;
  }, [apiBase]);

  useEffect(() => {
    const run = async () => {
      if (!healthUrl) {
        setState({ status: "error", message: "NEXT_PUBLIC_API_BASE_URL is not set; configure it in Render env vars." });
        return;
      }
      setState({ status: "loading" });
      try {
        const res = await fetch(healthUrl);
        const json = await res.json();
        setState({ status: "ok", message: JSON.stringify(json) });
      } catch (err: any) {
        setState({ status: "error", message: err?.message || "Ping failed" });
      }
    };
    run();
  }, [healthUrl]);

  return (
    <div className="card flex flex-col gap-2">
      <div className="font-semibold">Service status</div>
      <div className="text-sm text-slate-300">
        API base: <code className="text-brand-accent">{apiBase || "unset"}</code>
      </div>
      <div className="text-sm text-slate-300">
        Health URL: <code className="text-brand-accent">{healthUrl || "unavailable"}</code>
      </div>
      <div className="text-sm">
        State:{" "}
        <span className="font-semibold">
          {state.status}
          {state.status === "loading" && " …"}
        </span>
      </div>
      {state.message && <div className="text-xs text-slate-400 break-words">Response: {state.message}</div>}
    </div>
  );
}
