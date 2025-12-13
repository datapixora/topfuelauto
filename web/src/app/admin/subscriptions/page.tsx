"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { API_BASE, authHeaders } from "../../../lib/api";

export default function AdminSubscriptions() {
  const [subs, setSubs] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/metrics/subscriptions`, {
          credentials: "include",
          headers: { ...authHeaders() },
        });
        if (!res.ok) throw new Error("Failed to load subscriptions");
        const json = await res.json();
        setSubs(json.subscriptions || []);
      } catch (e: any) {
        setError(e.message);
      }
    };
    run();
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Subscriptions</CardTitle>
        {error && <div className="text-red-400 text-xs">Error: {error}</div>}
      </CardHeader>
      <CardContent>
        <Table>
          <THead>
            <TR>
              <TH>ID</TH>
              <TH>User</TH>
              <TH>Plan</TH>
              <TH>Status</TH>
            </TR>
          </THead>
          <TBody>
            {subs.map((s) => (
              <TR key={s.id}>
                <TD>{s.id}</TD>
                <TD>{s.user_id}</TD>
                <TD>{s.plan}</TD>
                <TD>{s.status}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </CardContent>
    </Card>
  );
}
