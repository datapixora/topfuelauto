export default function PricingPage() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="card">
        <div className="text-xl font-bold">Free</div>
        <p className="text-slate-400 text-sm">Search, browse, VIN decode.</p>
        <div className="text-3xl font-bold mt-4">$0</div>
      </div>
      <div className="card border-brand-gold/40">
        <div className="flex items-center gap-2">
          <div className="text-xl font-bold">Pro</div>
          <span className="text-xs px-2 py-1 rounded-full bg-brand-gold/20 text-brand-gold">Recommended</span>
        </div>
        <p className="text-slate-400 text-sm">VIN history, broker priority, saved searches (coming).</p>
        <div className="text-3xl font-bold mt-4">$39/mo</div>
      </div>
    </div>
  );
}