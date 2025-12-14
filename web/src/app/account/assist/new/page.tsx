"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopNav from "../../../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { createAssistCase, submitAssistCase } from "../../../../lib/api";
import { useAuth } from "../../../../components/auth/AuthProvider";

export default function AssistNewPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<"one_shot" | "watch">("one_shot");
  const [intake, setIntake] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user && !authLoading) {
      router.replace("/login?next=/account/assist/new");
    }
  }, [user, authLoading, router]);

  const onSubmit = async (run: boolean) => {
    setLoading(true);
    setError(null);
    try {
      const intakePayload = { notes: intake };
      const res = await createAssistCase({ title, mode, intake_payload: intakePayload });
      const id = res.case.id;
      if (run) {
        await submitAssistCase(id);
      }
      router.push(`/account/assist/${id}`);
    } catch (e: any) {
      setError(e.message || "Failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <TopNav />
      <Card>
        <CardHeader>
          <CardTitle>New Assist Case</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="text-sm text-slate-200">Title</div>
            <input
              className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Scout Tacoma under $25k"
            />
          </div>
          <div className="space-y-2">
            <div className="text-sm text-slate-200">Mode</div>
            <div className="flex gap-2">
              <Button variant={mode === "one_shot" ? "primary" : "ghost"} onClick={() => setMode("one_shot")}>
                One-shot
              </Button>
              <Button variant={mode === "watch" ? "primary" : "ghost"} onClick={() => setMode("watch")}>
                Watch
              </Button>
            </div>
            <div className="text-xs text-slate-500">Watch availability depends on your plan.</div>
          </div>
          <div className="space-y-2">
            <div className="text-sm text-slate-200">Notes / preferences</div>
            <textarea
              className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2"
              value={intake}
              onChange={(e) => setIntake(e.target.value)}
              rows={4}
            />
          </div>
          {error && <div className="text-red-400 text-sm">{error}</div>}
          <div className="flex gap-2">
            <Button onClick={() => onSubmit(false)} disabled={loading}>
              Save draft
            </Button>
            <Button onClick={() => onSubmit(true)} disabled={loading}>
              Submit & run
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
