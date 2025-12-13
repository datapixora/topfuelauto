"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { API_BASE } from "../../../lib/api";

type UserRow = { id: number; email: string; is_pro: boolean; is_admin: boolean };

export default function AdminUsers() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/metrics/users`, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to load users");
        const json = await res.json();
        setUsers(json.users || []);
      } catch (e: any) {
        setError(e.message);
      }
    };
    run();
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Users</CardTitle>
        {error && <div className="text-red-400 text-xs">Error: {error}</div>}
      </CardHeader>
      <CardContent>
        <Table>
          <THead>
            <TR>
              <TH>ID</TH>
              <TH>Email</TH>
              <TH>Pro</TH>
              <TH>Admin</TH>
            </TR>
          </THead>
          <TBody>
            {users.map((u) => (
              <TR key={u.id}>
                <TD>{u.id}</TD>
                <TD>{u.email}</TD>
                <TD>{u.is_pro ? "Yes" : "No"}</TD>
                <TD>{u.is_admin ? "Yes" : "No"}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </CardContent>
    </Card>
  );
}
