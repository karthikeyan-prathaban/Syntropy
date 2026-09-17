import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../lib/api";
import { Card, CardTitle } from "../components/primitives/Card";
import { AreaTrend } from "../components/charts/AreaTrend";
import { BarCompare } from "../components/charts/BarCompare";
import { Heatmap } from "../components/charts/Heatmap";
import { Waterfall } from "../components/charts/Waterfall";
import { Reveal } from "../motion/Reveal";
import { formatINR } from "../lib/format";

export function CashflowPage() {
  const cashflow = useQuery({ queryKey: ["cashflow"], queryFn: async () => (await analyticsApi.cashflow()).data });
  const forecast = useQuery({ queryKey: ["forecast"], queryFn: async () => (await analyticsApi.forecast()).data });
  const calendar = useQuery({ queryKey: ["calendar"], queryFn: async () => (await analyticsApi.calendar()).data });

  return (
    <div className="space-y-6">
      <Reveal>
        <h1 className="text-2xl font-bold">Cashflow</h1>
        <p className="text-muted text-sm">Income, expenses, and runway analysis</p>
      </Reveal>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Reveal>
          <Card>
            <CardTitle>Monthly cashflow</CardTitle>
            <AreaTrend data={cashflow.data || []} />
          </Card>
        </Reveal>
        <Reveal delay={0.05}>
          <Card>
            <CardTitle>Income vs expense</CardTitle>
            <BarCompare data={cashflow.data || []} />
          </Card>
        </Reveal>
      </div>

      <Reveal>
        <Card>
          <CardTitle>Net cashflow waterfall</CardTitle>
          <Waterfall
            data={(cashflow.data || []).map((c: { month: string; net: number }) => ({
              name: c.month.slice(5),
              value: c.net,
            }))}
          />
        </Card>
      </Reveal>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Reveal>
          <Card>
            <CardTitle>Runway forecast</CardTitle>
            <div className="mt-4 space-y-3">
              {(forecast.data || []).map((f: { month: string; projected_expense: number; projected_income: number; runway_months: number | null }) => (
                <div key={f.month} className="flex justify-between text-sm border-b border-border pb-2">
                  <span className="text-muted">{f.month}</span>
                  <span className="font-mono">Exp {formatINR(f.projected_expense)} · Runway {f.runway_months ?? "—"}mo</span>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
        <Reveal delay={0.1}>
          <Card>
            <CardTitle>Spending calendar (90d)</CardTitle>
            <div className="mt-4">
              <Heatmap data={(calendar.data || []).slice(-28)} />
            </div>
          </Card>
        </Reveal>
      </div>
    </div>
  );
}
