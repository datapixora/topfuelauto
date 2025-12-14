"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import TopNav from "../../components/TopNav";
import LoginForm from "../../components/auth/LoginForm";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";

function LoginContent() {
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || undefined;

  return (
    <div className="space-y-10">
      <TopNav />
      <div className="flex justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-xl">Sign in</CardTitle>
          </CardHeader>
          <CardContent>
            <LoginForm redirectTo={next && next.startsWith("/") ? next : undefined} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-10">
          <TopNav />
          <div className="text-slate-400">Loading login...</div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
