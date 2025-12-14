import Link from "next/link";
import TopNav from "../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";

export default function SignupPage() {
  return (
    <div className="space-y-10">
      <TopNav />
      <div className="flex justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-xl">Signup</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-slate-400">Signup is coming soon. Check back shortly while we finalize onboarding.</p>
            <Link
              href="/login"
              className="inline-flex w-full items-center justify-center rounded-md bg-brand-accent px-4 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-110"
            >
              Return to login
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
