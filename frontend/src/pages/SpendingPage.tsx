import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../lib/api";
import { Card, CardTitle } from "../components/primitives/Card";
import { DonutBreakdown } from "../components/charts/DonutBreakdown";
import { Reveal } from "../motion/Reveal";
import { formatINR } from "../lib/format";

export function SpendingPage() {
  const categories = useQuery({ queryKey: ["categories"], queryFn: async () => (await analyticsApi.categories()).data });
  const merchants = useQuery({ queryKey: ["merchants"], queryFn: async () => (await analyticsApi.merchants()).data });
  const recurring = useQuery({ queryKey: ["recurring"], queryFn: async () => (await analyticsApi.recurring()).data });

  return (
    <div className="space-y-6">
      <Reveal>
        <h1 className="text-2xl font-bold">Spending</h1>
        <p className="text-muted text-sm">Category breakdown, merchants, and subscriptions</p>
      </Reveal>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Reveal>
          <Card>
            <CardTitle>Category treemap</CardTitle>
            <DonutBreakdown data={categories.data || []} />
            <div className="mt-4 space-y-2">
              {(categories.data || []).map((c: { category: string; amount: number; percentage: number }) => (
                <div key={c.category} className="flex justify-between text-sm">
                  <span>{c.category}</span>
                  <span className="font-mono">{formatINR(c.amount)} ({c.percentage}%)</span>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
        <Reveal delay={0.1}>
          <Card>
            <CardTitle>Merchant leaderboard</CardTitle>
            <div className="mt-4 space-y-2">
              {(merchants.data || []).map((m: { merchant: string; amount: number; count: number; category: string }, i: number) => (
                <div key={m.merchant} className="flex items-center gap-3 text-sm">
                  <span className="text-muted w-5">{i + 1}</span>
                  <div className="flex-1">
                    <div className="font-medium">{m.merchant}</div>
                    <div className="text-xs text-muted">{m.category} · {m.count} txns</div>
                  </div>
                  <span className="font-mono">{formatINR(m.amount)}</span>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
      </div>

      <Reveal>
        <Card>
          <CardTitle>Recurring subscriptions</CardTitle>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            {(recurring.data || []).map((r: { merchant: string; amount: number; frequency: string; category: string }) => (
              <div key={r.merchant} className="rounded-xl bg-sunken p-4 flex justify-between">
                <div>
                  <div className="font-medium text-sm">{r.merchant}</div>
                  <div className="text-xs text-muted">{r.frequency} · {r.category}</div>
                </div>
                <span className="font-mono text-sm">{formatINR(r.amount)}</span>
              </div>
            ))}
            {!(recurring.data || []).length && (
              <p className="text-sm text-muted">No recurring patterns detected yet.</p>
            )}
          </div>
        </Card>
      </Reveal>
    </div>
  );
}
