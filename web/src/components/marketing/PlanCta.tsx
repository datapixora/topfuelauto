"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useAuth } from "../auth/AuthProvider";
import { startCheckout } from "../../lib/api";
import { getToken } from "../../lib/auth";
import { Button } from "../ui/button";

type PlanCtaProps = {
  planId: number;
  planSlug: string;
  label: string;
  emphasized?: boolean;
};

export default function PlanCta({ planId, planSlug, label, emphasized }: PlanCtaProps) {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const token = getToken();
  const hasToken = Boolean(token);

  const isCurrentPlan = useMemo(() => {
    if (!user) return false;
    if (user.plan_id != null) return user.plan_id === planId;
    if (user.plan_key) return user.plan_key === planSlug;
    return false;
  }, [planId, planSlug, user]);

  const onClick = async () => {
    setError(null);

    // If we have a token but auth is still loading, avoid mis-routing to /login.
    if (hasToken && loading) return;

    if (!getToken()) {
      router.push("/login?next=/pricing");
      return;
    }

    if (isCurrentPlan) return;

    if (planSlug === "free") {
      router.push("/search");
      return;
    }

    setBusy(true);
    try {
      const url = await startCheckout(planId, "month");
      window.location.href = url;
    } catch (e: any) {
      const msg = e instanceof Error ? e.message : "Unable to start checkout";
      setError(msg || "Unable to start checkout");
    } finally {
      setBusy(false);
    }
  };

  if (hasToken && loading) {
    return (
      <Button className="w-full" variant={emphasized ? "primary" : "ghost"} disabled>
        Checking account...
      </Button>
    );
  }

  if (isCurrentPlan) {
    return (
      <div className="space-y-2">
        <Button className="w-full" variant="ghost" disabled>
          Current Plan
        </Button>
        <div className="text-center text-xs text-slate-400">
          <Link href="/pricing" className="text-brand-accent hover:underline">
            Manage billing
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Button
        className="w-full"
        variant={emphasized ? "primary" : "ghost"}
        onClick={onClick}
        disabled={busy}
      >
        {busy ? "Redirecting..." : label}
      </Button>
      {error && <div className="text-xs text-red-400 text-center">{error}</div>}
    </div>
  );
}
