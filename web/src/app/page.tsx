import Link from "next/link";
import TopNav from "../components/TopNav";
import QuickPulse from "../components/system/QuickPulse";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Button } from "../components/ui/button";

type PublicPlan = {
  id: number;
  slug: string;
  name: string;
  price_monthly: number | null;
  currency: string;
  description: string | null;
  features: string[];
  is_featured: boolean;
  is_active: boolean;
  sort_order: number;
};

const valueProps = [
  {
    title: "Search Intelligence",
    body: "Aggregate auctions, classifieds, and broker feeds with fuzzy matching and normalization.",
  },
  {
    title: "Deal Score & Risk Flags",
    body: "Spot odometer concerns, salvage history, relisted VINs, and pricing gaps before you bid.",
  },
  {
    title: "Landed Cost Estimate",
    body: "Rough freight, duty, and local fees projected so you know the real delivered cost.",
  },
];

const howItWorks = [
  {
    title: "Search once",
    body: "Query multiple providers at once with filters tuned for make, model, year, and condition.",
  },
  {
    title: "Review the score",
    body: "We surface risks and a confidence score to help you triage the best listings fast.",
  },
  {
    title: "Decide with clarity",
    body: "See estimated landed cost and contact brokers without us holding the purchase funds.",
  },
];

const normalizeBase = (base: string) => {
  if (!base) return "";
  const trimmed = base.replace(/\/+$/, "");
  if (trimmed.endsWith("/api/v1")) return trimmed;
  return `${trimmed}/api/v1`;
};

const currencySymbol = (currency: string) => {
  const upper = (currency || "").toUpperCase();
  if (upper === "USD") return "$";
  if (upper === "EUR") return "€";
  if (upper === "GBP") return "£";
  return upper ? `${upper} ` : "";
};

async function fetchPublicPlans(): Promise<PublicPlan[]> {
  const apiBase = normalizeBase(process.env.NEXT_PUBLIC_API_BASE_URL || "");
  const endpoint = apiBase ? `${apiBase}/public/plans` : "/api/v1/public/plans";

  try {
    const res = await fetch(endpoint, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    const data = (await res.json()) as { plans?: PublicPlan[] };
    return Array.isArray(data?.plans) ? data.plans : [];
  } catch {
    return [];
  }
}

const faqs = [
  {
    q: "Do you take payment for vehicles?",
    a: "No. We are not a seller and never handle vehicle purchase money. You pay sellers or brokers directly; we only handle Stripe subscriptions.",
  },
  {
    q: "Which markets are covered?",
    a: "Coverage expands as providers are added via adapters. We start with major auctions and classifieds.",
  },
  {
    q: "How is the deal score built?",
    a: "Market comps, listing quality, VIN signals, and historical risk patterns feed a score you can sort and filter.",
  },
  {
    q: "Can I bring my own broker?",
    a: "Yes. We surface broker leads but stay neutral. You can invite your own broker and keep using the platform.",
  },
  {
    q: "Is there an API?",
    a: "An authenticated API is in progress for inventory, scoring, and export workflows.",
  },
];

const makes = ["Any make", "Nissan", "Toyota", "BMW"];
const models = ["Any model", "GT-R", "Supra", "M3"];
const years = ["Any year", "2024", "2020-2023", "2015-2019"];

function SkeletonResultCard() {
  return (
    <Card className="border-slate-800 bg-slate-900/60">
      <div className="animate-pulse space-y-3 p-4">
        <div className="h-3 w-1/2 rounded bg-slate-800" />
        <div className="h-4 w-3/4 rounded bg-slate-800" />
        <div className="h-3 w-1/3 rounded bg-slate-800" />
      </div>
    </Card>
  );
}

export default async function HomePage() {
  const plans = await fetchPublicPlans();

  return (
    <div className="space-y-12">
      <TopNav />

      <section className="grid items-center gap-10 md:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <div className="inline-flex items-center rounded-full border border-slate-800 bg-slate-900/70 px-3 py-1 text-xs text-slate-300">
            Vehicle intelligence without holding buyer funds
          </div>
          <div className="space-y-3">
            <h1 className="text-4xl font-bold leading-tight md:text-5xl">
              Find vehicles worldwide. Understand the real deal before you bid.
            </h1>
            <p className="text-lg text-slate-300">
              Search listings, score deals, flag risks, and estimate landed cost - rule-based first.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/search"
              className="inline-flex items-center rounded-md bg-brand-accent px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
            >
              Start searching (Free)
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center rounded-md border border-slate-700 px-5 py-3 text-sm font-semibold text-slate-100 transition hover:bg-slate-800"
            >
              See Plans
            </Link>
          </div>
          <div className="text-xs text-slate-400">
            No credit card. We never handle vehicle purchase money.
          </div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Not a seller | Not a financial intermediary | Stripe subscriptions only
          </div>
        </div>
        <QuickPulse />
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Search preview</h2>
            <p className="text-sm text-slate-400">UI only for now. Connects to search soon.</p>
          </div>
          <Link href="/search" className="text-sm text-brand-accent hover:underline">
            Open full search
          </Link>
        </div>
        <Card className="border-slate-800 bg-slate-900/70">
          <CardContent className="space-y-5 pt-6">
            <div className="grid gap-3 md:grid-cols-[2fr_1fr_1fr_1fr_auto]">
              <div className="space-y-2">
                <Label htmlFor="preview-search">Search query</Label>
                <Input id="preview-search" placeholder="e.g. Nissan GT-R 2005" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="make">Make</Label>
                <select id="make" className="h-10 w-full rounded-md border border-slate-800 bg-slate-900 px-3 text-sm text-slate-100">
                  {makes.map((make) => (
                    <option key={make}>{make}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <select id="model" className="h-10 w-full rounded-md border border-slate-800 bg-slate-900 px-3 text-sm text-slate-100">
                  {models.map((model) => (
                    <option key={model}>{model}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="year">Year</Label>
                <select id="year" className="h-10 w-full rounded-md border border-slate-800 bg-slate-900 px-3 text-sm text-slate-100">
                  {years.map((year) => (
                    <option key={year}>{year}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <Button type="button" className="w-full">Search</Button>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {[1, 2, 3].map((id) => (
                <SkeletonResultCard key={id} />
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {valueProps.map((item) => (
          <Card key={item.title} className="border-slate-800 bg-slate-900/70">
            <CardHeader>
              <CardTitle>{item.title}</CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">{item.body}</CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {howItWorks.map((step, idx) => (
          <Card key={step.title} className="border-slate-800 bg-slate-900/70">
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-sm font-semibold">
                  {idx + 1}
                </span>
                {step.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">{step.body}</CardContent>
          </Card>
        ))}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Plans</h2>
            <p className="text-sm text-slate-400">Choose the right fit and upgrade inside pricing.</p>
          </div>
          <Link href="/pricing" className="text-sm text-brand-accent hover:underline">
            See Plans
          </Link>
        </div>
        {plans.length === 0 ? (
          <Card className="border-slate-800 bg-slate-900/70">
            <CardContent className="py-6 text-sm text-slate-300">
              Plans are being updated right now. Please check back soon or visit the pricing page.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {plans.map((plan) => {
              const bulletFeatures = Array.isArray(plan.features) ? plan.features : [];
              const visibleFeatures = bulletFeatures.slice(0, 6);
              const truncated = bulletFeatures.length > visibleFeatures.length;
              const symbol = currencySymbol(plan.currency);
              const priceText =
                plan.price_monthly == null ? "Custom" : `${symbol}${plan.price_monthly}`;
              const ctaLabel = plan.slug === "pro" ? "Upgrade to Pro" : "Get Started";
              const signupHref = `/signup?plan=${encodeURIComponent(plan.slug)}`;

              return (
                <Card
                  key={plan.id}
                  className={`relative border-slate-800 bg-slate-900/70 ${plan.is_featured ? "border-brand-accent/60 bg-slate-900/85 md:scale-[1.02]" : ""}`}
                >
                  {plan.is_featured && (
                    <div className="absolute right-4 top-4 rounded-full bg-brand-gold/20 px-3 py-1 text-xs font-semibold text-brand-gold">
                      Most Popular
                    </div>
                  )}
                  <CardHeader className="space-y-2">
                    <CardTitle className="text-xl">{plan.name}</CardTitle>
                    <div className="flex items-end gap-2">
                      <div className="text-3xl font-semibold text-slate-50">{priceText}</div>
                      <div className="pb-1 text-sm text-slate-400">{plan.price_monthly == null ? "" : "/month"}</div>
                    </div>
                    {plan.description && <div className="text-sm text-slate-300">{plan.description}</div>}
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <ul className="space-y-2 text-sm text-slate-300">
                      {visibleFeatures.map((feature) => (
                        <li key={feature} className="flex gap-2">
                          <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-brand-accent" />
                          <span>{feature}</span>
                        </li>
                      ))}
                      {truncated && (
                        <li className="flex gap-2 text-slate-400">
                          <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-slate-600" />
                          <span>and more</span>
                        </li>
                      )}
                    </ul>

                    <Link
                      href={signupHref}
                      className={`inline-flex w-full items-center justify-center rounded-md px-5 py-2 text-sm font-semibold transition ${plan.is_featured ? "bg-brand-accent text-slate-950 hover:brightness-110" : "border border-slate-700 text-slate-100 hover:bg-slate-800"}`}
                    >
                      {ctaLabel}
                    </Link>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
        <div className="flex justify-center">
          <Link
            href="/pricing"
            className="inline-flex items-center rounded-md bg-brand-accent px-5 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-110"
          >
            See Plans
          </Link>
        </div>
      </section>

      <section>
        <Card className="border-slate-800 bg-slate-900/70">
          <CardHeader>
            <CardTitle>Providers & coverage</CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300">
            Provider logos and coverage map will live here. We are wiring auctions, classifieds, and broker networks into one pane.
          </CardContent>
        </Card>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">FAQ</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {faqs.map((item) => (
            <Card key={item.q} className="border-slate-800 bg-slate-900/70">
              <CardHeader>
                <CardTitle className="text-base">{item.q}</CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 text-sm leading-relaxed">{item.a}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      <footer className="flex flex-col gap-2 border-t border-slate-800 pt-6 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
        <div>Copyright {new Date().getFullYear()} TopFuelAuto. Search-first vehicle intelligence.</div>
        <div className="flex gap-4">
          <Link href="/pricing" className="hover:text-white">Pricing</Link>
          <Link href="/login" className="hover:text-white">Login</Link>
          <Link href="/dashboard" className="hover:text-white">Dashboard</Link>
        </div>
      </footer>
    </div>
  );
}
