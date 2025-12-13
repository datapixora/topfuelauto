"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { Button } from "../../../components/ui/button";
import { API_BASE } from "../../../lib/api";

export default function AdminProviders() {
  const [providers, setProviders] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/providers/status`, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to load providers");
        const json = await res.json();
        setProviders(json.providers || []);
      } catch (e: any) {
        setError(e.message);
      }
    };
    run();
  }, []);

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Providers</CardTitle>
        {error && <div className="text-red-400 text-xs">Error: {error}</div>}
      </CardHeader>
      <CardContent>
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Status</TH>
              <TH>Last sync</TH>
              <TH></TH>
            </TR>
          </THead>
          <TBody>
            {providers.map((p, idx) => (
              <TR key={idx}>
                <TD>{p.name}</TD>
                <TD>{p.status || "unknown"}</TD>
                <TD>{p.last_sync || "—"}</TD>
                <TD>
                  <Button variant="ghost">Run sync</Button>
                </TD>
              </TR>
            ))}
            {providers.length === 0 && (
              <TR>
                <TD colSpan={4} className="text-slate-500 text-sm py-6 text-center">
                  No providers configured yet.
                </TD>
              </TR>
            )}
          </TBody>
        </Table>
      </CardContent>
    </Card>
  );
}
