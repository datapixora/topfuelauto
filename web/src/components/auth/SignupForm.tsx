"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { signup } from "../../lib/api";
import { setToken } from "../../lib/auth";
import { Alert, AlertDescription } from "../ui/alert";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type SignupFormProps = {
  onSuccess?: (token: string) => void;
  redirectTo?: string;
};

export default function SignupForm({ onSuccess, redirectTo }: SignupFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      const res = await signup(email, password);
      setToken(res.access_token);
      onSuccess?.(res.access_token);
      const target = redirectTo && redirectTo.startsWith("/") ? redirectTo : "/search";
      router.push(target);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to sign up.";
      setError(message || "Unable to sign up.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          name="password"
          type="password"
          placeholder="********"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirm">Confirm password</Label>
        <Input
          id="confirm"
          name="confirm"
          type="password"
          placeholder="********"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
          minLength={8}
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" disabled={loading} className="w-full flex items-center justify-center gap-2">
        {loading && <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-transparent" />}
        <span>{loading ? "Creating account..." : "Create account"}</span>
      </Button>

      <div className="text-sm text-slate-400 text-center">
        Already have an account?{" "}
        <Link href="/login" className="text-brand-accent hover:underline">
          Sign in
        </Link>
      </div>
    </form>
  );
}
