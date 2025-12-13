"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../components/ui/card";
import { API_BASE } from "../../../../lib/api";

export default function AdminUserDetail() {
  const params = useParams();
  const id = params?.id as string;
  const [user, setUser] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/admin/users/${id}`, { credentials: "include" });
        if (!res.ok) throw new Error("Failed to load user");
        const json = await res.json();
        setUser(json);
      } catch (e: any) {
        setError(e.message);
      }
    };
    run();
  }, [id]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>User #{id}</CardTitle>
        {error && <div className="text-red-400 text-xs">Error: {error}</div>}
      </CardHeader>
      <CardContent>
        {user ? (
          <div className="space-y-2 text-sm">
            <div>Email: {user.email}</div>
            <div>Pro: {user.is_pro ? "Yes" : "No"}</div>
            <div>Admin: {user.is_admin ? "Yes" : "No"}</div>
          </div>
        ) : (
          <div className="text-slate-400 text-sm">Loading...</div>
        )}
      </CardContent>
    </Card>
  );
}
