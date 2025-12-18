"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import TopNav from "../../components/TopNav";
import LoginForm from "../../components/auth/LoginForm";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { getCurrentUser } from "../../lib/api";
import { getToken, clearToken } from "../../lib/auth";
import { getNextUrl } from "../../lib/utils";

function LoginContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const next = searchParams.get("next") || undefined;
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();

      // No token, show login form
      if (!token) {
        setCheckingAuth(false);
        return;
      }

      // Token exists, verify it's valid
      try {
        const user = await getCurrentUser();

        // User is authenticated, determine redirect target
        let redirectTarget: string;

        if (next) {
          // Use validated next parameter
          redirectTarget = getNextUrl(next, user.is_admin ? "/admin" : "/dashboard");
        } else {
          // Default redirect based on user role
          redirectTarget = user.is_admin ? "/admin" : "/dashboard";
        }

        router.push(redirectTarget);
      } catch (error) {
        // Token is invalid, clear it and show login form
        clearToken();
        setCheckingAuth(false);
      }
    };

    void checkAuth();
  }, [next, router]);

  // Show loading state while checking authentication
  if (checkingAuth) {
    return (
      <div className="space-y-10">
        <TopNav />
        <div className="flex justify-center">
          <Card className="w-full max-w-md">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center gap-4 py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-brand-accent" />
                <p className="text-sm text-slate-400">Checking session...</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

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
