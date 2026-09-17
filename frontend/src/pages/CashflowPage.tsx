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
            <div className="flex gap-6 mt-4">
              <div>
                <div className="text-muted text-xs">Runway</div>
                <div className="font-mono font-medium">
                  {forecast.data?.runway_months != null ? `${forecast.data.runway_months} mo` : "Cashflow positive"}
                </div>
              </div>
              <div>
                <div className="text-muted text-xs">Net monthly</div>
                <div className={`font-mono font-medium ${(forecast.data?.net_monthly ?? 0) >= 0 ? "text-jade" : "text-ink"}`}>
                  {formatINR(forecast.data?.net_monthly ?? 0)}
                </div>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              {(forecast.data?.points ?? []).map((f) => (
                <div key={f.month} className="flex justify-between text-sm border-b border-border pb-2">
                  <div>
                    <div className="text-muted">{f.month}</div>
                    <div className="text-muted text-xs">
                      Committed {formatINR(f.committed_expense)} · Variable {formatINR(f.variable_expense)}
                    </div>
                  </div>
                  <span className="font-mono">
                    Exp {formatINR(f.projected_expense)} · Bal {formatINR(f.projected_balance)}
                  </span>
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
