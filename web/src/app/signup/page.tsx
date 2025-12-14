import Link from "next/link";
import TopNav from "../../components/TopNav";
import SignupForm from "../../components/auth/SignupForm";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";

export default function SignupPage() {
  return (
    <div className="space-y-10">
      <TopNav />
      <div className="flex justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-xl">Create your account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <SignupForm />
            <div className="text-xs text-center text-slate-400">
              Already have an account?{" "}
              <Link href="/login" className="text-brand-accent hover:underline">
                Sign in
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
