"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { apiGet } from "../../../lib/api";

export default function AdminSubscriptions() {
  const [subs, setSubs] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const json = await apiGet<{ subscriptions: any[] }>("/admin/metrics/subscriptions");
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
