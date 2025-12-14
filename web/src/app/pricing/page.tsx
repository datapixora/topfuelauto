"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { listPlans, startCheckout } from "../../lib/api";
import { Plan } from "../../lib/types";
import { getToken } from "../../lib/auth";

const intervals: Array<"month" | "year"> = ["month", "year"];

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [interval, setInterval] = useState<"month" | "year">("month");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const load = async () => {
      try {
        const res = await listPlans();
        setPlans(res);
      } catch (e: any) {
        setError(e.message || "Failed to load plans");
      }
    };
    void load();
  }, []);

  const onCheckout = async (planId: number) => {
    const plan = plans.find((p) => p.id === planId);
    if (plan?.key === "free") {
      router.push("/search");
      return;
    }
    if (!getToken()) {
      router.push("/login?next=/pricing");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const url = await startCheckout(planId, interval);
      window.location.href = url;
    } catch (e: any) {
      setError(e.message || "Unable to start checkout");
    } finally {
      setLoading(false);
    }
  };

  const badgeFor = (plan: Plan) => {
    if (plan.key === "free") return null;
    if (plan.key === "pro") return "Recommended";
    return null;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Pricing</h1>
        <p className="text-slate-400 text-sm">Choose a plan. Billing handled via Stripe checkout.</p>
        <div className="flex gap-2">
          {intervals.map((i) => (
            <Button key={i} variant={i === interval ? "primary" : "ghost"} onClick={() => setInterval(i)}>
              {i === "month" ? "Monthly" : "Yearly"}
            </Button>
          ))}
        </div>
      </div>

      {error && <div className="text-red-400 text-sm">Error: {error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {plans.map((plan) => {
          const priceId =
            interval === "month" ? plan.stripe_price_id_monthly : plan.stripe_price_id_yearly;
          const disabled = !priceId || loading;
          return (
            <Card key={plan.id} className="border-slate-800 bg-slate-900/70">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>{plan.name}</CardTitle>
                {badgeFor(plan) && (
                  <span className="text-xs px-2 py-1 rounded-full bg-brand-gold/20 text-brand-gold">{badgeFor(plan)}</span>
                )}
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-sm text-slate-400">
                  {plan.searches_per_day ? `${plan.searches_per_day} searches/day` : "Unlimited searches"}
                </div>
                <div className="space-y-2">
                  <Button
                    className="w-full"
                    disabled={disabled}
                    onClick={() => onCheckout(plan.id)}
                    title={!priceId ? "Not configured" : ""}
                  >
                    {plan.key === "free" ? "Start free" : `Upgrade (${interval === "month" ? "Monthly" : "Yearly"})`}
                  </Button>
                  {disabled && plan.key !== "free" && (
                    <div className="text-xs text-amber-400">Billing not configured yet.</div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
