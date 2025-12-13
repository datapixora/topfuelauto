"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { API_BASE } from "../../../lib/api";

export default function AdminSearchAnalytics() {
  const [top, setTop] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/metrics/searches`, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to load search metrics");
        const json = await res.json();
        setTop(json.top_queries || []);
      } catch (e: any) {
        setError(e.message);
      }
    };
    run();
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search analytics</CardTitle>
        {error && <div className="text-red-400 text-xs">Error: {error}</div>}
      </CardHeader>
      <CardContent>
        <Table>
          <THead>
            <TR>
              <TH>Query</TH>
              <TH>Results</TH>
            </TR>
          </THead>
          <TBody>
            {top.map((t, idx) => (
              <TR key={idx}>
                <TD>{t.query}</TD>
                <TD>{t.results_count ?? "—"}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </CardContent>
    </Card>
  );
}
