"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, AlertDescription } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { cn } from "../../lib/utils";

const HEALTH_TIMEOUT_MS = 4000;

type Status = "idle" | "loading" | "ok" | "error";

type PulseState = {
  status: Status;
  latencyMs?: number;
  message?: string;
  lastChecked?: Date;
  checkedUrl?: string;
};

type HealthUrls = {
  healthUrl: string | null;
  fallbackUrl: string | null;
  displayBase: string | null;
};

const computeHealthUrls = (rawBase?: string): HealthUrls => {
  if (!rawBase) return { healthUrl: null, fallbackUrl: null, displayBase: null };
  const trimmed = rawBase.replace(/\/+$/, "");
  const hasApiV1 = trimmed.endsWith("/api/v1");
  const healthUrl = hasApiV1 ? `${trimmed}/health` : `${trimmed}/api/v1/health`;
  const baseRoot = hasApiV1 ? trimmed.slice(0, -"/api/v1".length) : trimmed;
  const fallbackUrl = baseRoot ? `${baseRoot}/` : null;
  return { healthUrl, fallbackUrl, displayBase: baseRoot || trimmed };
};

type QuickPulseProps = {
  className?: string;
};

export default function QuickPulse({ className }: QuickPulseProps) {
  const urls = useMemo(() => computeHealthUrls(process.env.NEXT_PUBLIC_API_BASE_URL), []);
  const [state, setState] = useState<PulseState>({ status: "idle" });

  const attemptPing = useCallback(async (url: string) => {
    const start = performance.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
    try {
      const res = await fetch(url, { signal: controller.signal });
      const end = performance.now();
      const latencyMs = Math.round(end - start);
      if (!res.ok) {
        return { ok: false as const, message: `Status ${res.status}`, url };
      }
      return { ok: true as const, latencyMs, url };
    } catch (err: any) {
      const message =
        err?.name === "AbortError"
          ? `Timeout after ${HEALTH_TIMEOUT_MS} ms`
          : err?.message || "Request failed";
      return { ok: false as const, message, url };
    } finally {
      clearTimeout(timeout);
    }
  }, []);

  const runCheck = useCallback(async () => {
    if (!urls.healthUrl) {
      setState({
        status: "error",
        message: "NEXT_PUBLIC_API_BASE_URL is not set.",
        lastChecked: new Date(),
      });
      return;
    }

    setState((prev) => ({ ...prev, status: "loading" }));

    const primary = await attemptPing(urls.healthUrl);
    let result = primary;

    if (!primary.ok && urls.fallbackUrl) {
      const fallback = await attemptPing(urls.fallbackUrl);
      if (fallback.ok) {
        result = fallback;
      } else {
        const combined = [primary.message, fallback.message].filter(Boolean).join("; ");
        result = { ok: false as const, message: combined || "Health check failed", url: fallback.url };
      }
    }

    const now = new Date();
    if (result.ok) {
      setState({
        status: "ok",
        latencyMs: result.latencyMs,
        checkedUrl: result.url,
        lastChecked: now,
      });
    } else {
      setState({
        status: "error",
        message: result.message,
        checkedUrl: result.url,
        lastChecked: now,
      });
    }
  }, [attemptPing, urls.fallbackUrl, urls.healthUrl]);

  useEffect(() => {
    runCheck();
  }, [runCheck]);

  const statusBadge = (() => {
    if (state.status === "loading") {
      return (
        <div className="inline-flex items-center gap-2 text-slate-300">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-transparent" />
          Checking API...
        </div>
      );
    }
    if (state.status === "ok") {
      return (
        <div className="inline-flex items-center gap-2 text-emerald-300">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          API online {state.latencyMs !== undefined ? `• ${state.latencyMs} ms` : ""}
        </div>
      );
    }
    if (state.status === "error") {
      return (
        <div className="inline-flex items-center gap-2 text-red-200">
          <span className="h-2 w-2 rounded-full bg-red-400" />
          API unreachable
        </div>
      );
    }
    return null;
  })();

  return (
    <Card className={cn("border-slate-800 bg-slate-900/70", className)}>
      <CardHeader>
        <CardTitle className="text-lg">Quick pulse</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-slate-300">
        {statusBadge}

        {state.status === "ok" && state.checkedUrl && (
          <div className="text-xs text-slate-400">Checked: {state.checkedUrl}</div>
        )}

        {state.status === "error" && (
          <Alert variant="destructive">
            <AlertDescription>{state.message || "Health check failed"}</AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-between text-xs text-slate-400">
          <div>
            Base: <code className="text-brand-accent">{urls.displayBase || "not set"}</code>
          </div>
          {state.lastChecked && <div>Last checked: {state.lastChecked.toLocaleTimeString()}</div>}
        </div>

        <div className="flex gap-2">
          <Button onClick={runCheck} disabled={state.status === "loading"}>
            {state.status === "loading" ? "Checking..." : "Retry"}
          </Button>
          {state.latencyMs !== undefined && state.status === "ok" && (
            <div className="text-xs text-slate-400 self-center">Latency is client-side measured.</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
