"use client";

import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";

const plans = [
  { name: "Free", price: "$0", quota: "Basic search", features: ["Search", "VIN decode"] },
  { name: "Pro", price: "$39/mo", quota: "Up to 100 saved searches", features: ["VIN history", "Broker priority"] },
  { name: "Ultimate", price: "$99/mo", quota: "Unlimited", features: ["Priority support", "Bulk tools"] },
];

export default function AdminPlans() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {plans.map((plan) => (
        <Card key={plan.name}>
          <CardHeader>
            <CardTitle>{plan.name}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-2xl font-semibold">{plan.price}</div>
            <div className="text-sm text-slate-400">{plan.quota}</div>
            <ul className="text-sm list-disc list-inside text-slate-300">
              {plan.features.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <Button variant="ghost">Edit</Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
