"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "../../../components/ui/table";
import { Button } from "../../../components/ui/button";
import Link from "next/link";
import { apiGet, authHeaders, API_BASE } from "../../../lib/api";

type UserRow = {
  id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  plan_id: number | null;
  plan_name: string | null;
};

type PlanRow = { id: number; name: string; key: string };

export default function AdminUsers() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [{ users }, planRes] = await Promise.all([
        apiGet<{ users: UserRow[] }>("/admin/metrics/users"),
        apiGet<{ plans: PlanRow[] }>("/admin/plans"),
      ]);
      setUsers(users || []);
      setPlans(planRes.plans || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const changeStatus = async (userId: number, isActive: boolean) => {
    if (!window.confirm(isActive ? "Reactivate this user?" : "Deactivate this user?")) return;
    setSaving(userId);
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ is_active: isActive }),
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to update status");
    } finally {
      setSaving(null);
    }
  };

  const changePlan = async (userId: number, planId: number) => {
    setSaving(userId);
    try {
      const res = await fetch(`${API_BASE}/admin/users/${userId}/plan`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ plan_id: planId }),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Failed (${res.status}): ${txt}`);
      }
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to change plan");
    } finally {
      setSaving(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Users</CardTitle>
        {error && <div className="text-red-400 text-xs">Error: {error}</div>}
      </CardHeader>
      <CardContent>
        {loading && <div className="text-slate-400 text-sm mb-3">Loading...</div>}
        <Table>
          <THead>
            <TR>
              <TH>ID</TH>
              <TH>Email</TH>
              <TH>Status</TH>
              <TH>Plan</TH>
              <TH>Admin</TH>
              <TH>Actions</TH>
            </TR>
          </THead>
          <TBody>
            {users.map((u) => (
              <TR key={u.id}>
                <TD>{u.id}</TD>
                <TD>
                  <Link href={`/admin/users/${u.id}`} className="text-brand-accent hover:underline">
                    {u.email}
                  </Link>
                </TD>
                <TD>
                  <span
                    className={`rounded-full px-2 py-1 text-xs ${
                      u.is_active ? "bg-emerald-500/20 text-emerald-200" : "bg-red-500/20 text-red-200"
                    }`}
                  >
                    {u.is_active ? "Active" : "Disabled"}
                  </span>
                </TD>
                <TD>
                  <select
                    className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
                    value={u.plan_id ?? plans.find((p) => p.key === "free")?.id ?? ""}
                    onChange={(e) => changePlan(u.id, Number(e.target.value))}
                    disabled={saving === u.id}
                  >
                    {plans.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </TD>
                <TD>{u.is_admin ? "Yes" : "No"}</TD>
                <TD className="space-x-2">
                  <Button
                    variant="ghost"
                    onClick={() => changeStatus(u.id, !u.is_active)}
                    disabled={saving === u.id}
                  >
                    {u.is_active ? "Deactivate" : "Reactivate"}
                  </Button>
                </TD>
              </TR>
            ))}
            {users.length === 0 && (
              <TR>
                <TD colSpan={6} className="text-center text-slate-500 py-4">
                  No users yet.
                </TD>
              </TR>
            )}
          </TBody>
        </Table>
      </CardContent>
    </Card>
  );
}
