import Link from "next/link";
import TopNav from "../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";

export default function DashboardPage() {
  return (
    <div className="space-y-10">
      <TopNav />
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Dashboard</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-slate-400">Your personalized dashboard is on the way. We will surface searches, saved vehicles, and plan status here.</p>
          <Link href="/search" className="inline-flex items-center text-brand-accent hover:underline">
            Go to search
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
