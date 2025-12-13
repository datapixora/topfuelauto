"use client";

import { useEffect, useState } from "react";

type PingState = { status: "idle" | "loading" | "ok" | "error"; message?: string };

export default function HomeStatus() {
  const [state, setState] = useState<PingState>({ status: "idle" });
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;

  useEffect(() => {
    const run = async () => {
      if (!apiBase) {
        setState({ status: "error", message: "NEXT_PUBLIC_API_BASE_URL not set" });
        return;
      }
      setState({ status: "loading" });
      try {
        const res = await fetch(`${apiBase}/health`);
        const json = await res.json();
        setState({ status: "ok", message: JSON.stringify(json) });
      } catch (err: any) {
        setState({ status: "error", message: err?.message || "Ping failed" });
      }
    };
    run();
  }, [apiBase]);

  return (
    <div className="card flex flex-col gap-2">
      <div className="font-semibold">Service status</div>
      <div className="text-sm text-slate-300">
        API base: <code className="text-brand-accent">{apiBase || "unset"}</code>
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
