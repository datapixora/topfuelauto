"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import TopNav from "../../../../components/TopNav";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { assistCaseDetail, submitAssistCase } from "../../../../lib/api";
import { Button } from "../../../../components/ui/button";

export default function AssistDetailPage() {
  const params = useParams();
  const caseId = params?.id as string;
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await assistCaseDetail(Number(caseId));
      setData(res);
    } catch (e: any) {
      setError(e.message || "Failed to load case");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) void load();
  }, [caseId]);

  const rerun = async () => {
    await submitAssistCase(Number(caseId));
    await load();
  };

  const caseInfo = data?.case;

  return (
    <div className="space-y-6">
      <TopNav />
      {error && <div className="text-red-400 text-sm">{error}</div>}
      {caseInfo && (
        <>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-semibold">{caseInfo.title || "Assist Case"}</div>
              <div className="text-xs text-slate-400">
                {caseInfo.mode} • {caseInfo.status}
              </div>
            </div>
            <Button onClick={rerun}>Rerun</Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Report</CardTitle>
            </CardHeader>
            <CardContent className="prose prose-invert">
              {data.artifacts?.find((a: any) => a.type === "report_md")?.content_text || "No report yet."}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {data.steps?.map((s: any) => (
                  <div key={s.id} className="flex items-center justify-between text-sm">
                    <div>{s.step_key}</div>
                    <div className="text-xs text-slate-400">{s.status}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Inputs</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-xs bg-slate-900 p-3 rounded">{JSON.stringify(caseInfo, null, 2)}</pre>
            </CardContent>
          </Card>
        </>
      )}
      {loading && <div className="text-slate-400 text-sm">Loading...</div>}
    </div>
  );
}
