import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";

const plans = [
  {
    name: "Free",
    price: "$0",
    desc: "Search, browse, VIN decode. Great for quick checks.",
  },
  {
    name: "Pro",
    price: "$39/mo",
    desc: "Deal scoring, alerts, risk flags, and saved searches (coming).",
    badge: "Recommended",
  },
  {
    name: "Ultimate",
    price: "Talk to us",
    desc: "Multi-seat access, exports, and adapter prioritization for teams.",
  },
];

export default function PricingPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Pricing</h1>
        <p className="text-slate-400 text-sm">Coming next: Stripe checkout. Pick a plan and start searching today.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {plans.map((plan) => (
          <Card key={plan.name} className="border-slate-800 bg-slate-900/70">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{plan.name}</CardTitle>
              {plan.badge && (
                <span className="text-xs px-2 py-1 rounded-full bg-brand-gold/20 text-brand-gold">{plan.badge}</span>
              )}
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-3xl font-bold">{plan.price}</div>
              <p className="text-slate-400 text-sm">{plan.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Link
        href="/search"
        className="inline-flex w-full items-center justify-center rounded-md bg-brand-accent px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110 md:w-auto"
      >
        Start searching (Free)
      </Link>
    </div>
  );
}
