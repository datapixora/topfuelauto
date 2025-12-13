export default function ProBadge({ show, label = "Pro" }: { show?: boolean; label?: string }) {
  if (!show) return null;
  return (
    <span className="text-xs px-2 py-1 rounded-full bg-brand-gold/20 text-brand-gold border border-brand-gold/40">
      {label}
    </span>
  );
}