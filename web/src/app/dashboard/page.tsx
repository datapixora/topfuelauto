"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopNav from "../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { getToken } from "../../lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login?next=/dashboard");
      return;
    }
    setReady(true);
  }, [router]);

  return (
    <div className="space-y-10">
      <TopNav />
      {!ready ? (
        <div className="text-slate-400">Redirecting to login...</div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Dashboard</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-slate-400">Dashboard is being built. Soon you will see searches, saved vehicles, and plan status here.</p>
            <div className="flex gap-4 text-sm">
              <Link href="/" className="text-brand-accent hover:underline">
                Back to Home
              </Link>
              <Link href="/pricing" className="text-brand-accent hover:underline">
                View pricing
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
