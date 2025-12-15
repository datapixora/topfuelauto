import Link from 'next/link';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-slate-800 mt-16">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* About Section */}
          <div>
            <h3 className="font-semibold text-white mb-3">TopFuel Auto</h3>
            <p className="text-sm text-slate-400">
              Find vehicles across the web with our meta-search platform.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="font-semibold text-white mb-3">Product</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/search" className="text-slate-400 hover:text-white transition-colors">
                  Search
                </Link>
              </li>
              <li>
                <Link href="/pricing" className="text-slate-400 hover:text-white transition-colors">
                  Pricing
                </Link>
              </li>
              <li>
                <Link href="/account/assist" className="text-slate-400 hover:text-white transition-colors">
                  Assist
                </Link>
              </li>
              <li>
                <Link href="/account/alerts" className="text-slate-400 hover:text-white transition-colors">
                  Alerts
                </Link>
              </li>
            </ul>
          </div>

          {/* Account */}
          <div>
            <h3 className="font-semibold text-white mb-3">Account</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/login" className="text-slate-400 hover:text-white transition-colors">
                  Login
                </Link>
              </li>
              <li>
                <Link href="/signup" className="text-slate-400 hover:text-white transition-colors">
                  Sign Up
                </Link>
              </li>
              <li>
                <Link href="/account/subscription" className="text-slate-400 hover:text-white transition-colors">
                  Subscription
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
                  Dashboard
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="font-semibold text-white mb-3">Legal</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/legal/terms" className="text-slate-400 hover:text-white transition-colors">
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link href="/legal/privacy" className="text-slate-400 hover:text-white transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/legal/disclaimer" className="text-slate-400 hover:text-white transition-colors">
                  Disclaimer
                </Link>
              </li>
              <li>
                <Link href="/legal/takedown" className="text-slate-400 hover:text-white transition-colors">
                  Contact & Takedown
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="border-t border-slate-800 mt-8 pt-6 text-sm text-slate-500 text-center">
          <p>
            © {currentYear} TopFuel Auto. All rights reserved. We are a vehicle meta-search platform.
            We do not own, sell, or broker vehicles.
          </p>
        </div>
      </div>
    </footer>
  );
}
