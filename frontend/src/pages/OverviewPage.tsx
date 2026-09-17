import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "../lib/api";
import { Card, CardTitle, CardValue } from "../components/primitives/Card";
import { CountUp } from "../motion/CountUp";
import { AreaTrend } from "../components/charts/AreaTrend";
import { DonutBreakdown } from "../components/charts/DonutBreakdown";
import { RadialScore } from "../components/charts/RadialScore";
import { Badge } from "../components/primitives/Badge";
import { Reveal } from "../motion/Reveal";
import { formatINR } from "../lib/format";
import { Button } from "../components/primitives/Button";
import { useNavigate } from "react-router-dom";

export function OverviewPage() {
  const navigate = useNavigate();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await dashboardApi.get()).data,
  });

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 skeleton rounded-2xl" />
        ))}
      </div>
    );
  }

  const loadDemo = async () => {
    await dashboardApi.loadMock();
    refetch();
  };

  return (
    <div className="space-y-6">
      <Reveal>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Good day, {data.user.name.split(" ")[0]}</h1>
            <p className="text-muted text-sm mt-1">Your financial analytics at a glance</p>
          </div>
          <div className="flex gap-2">
            {data.total_balance === 0 && (
              <Button variant="outline" onClick={loadDemo}>Load demo data</Button>
            )}
            <Button onClick={() => navigate("/app/accounts")}>Link bank</Button>
          </div>
        </div>
      </Reveal>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Net worth", value: data.total_balance, prefix: "₹" },
          { label: "Income", value: data.total_income, prefix: "₹", color: "text-jade" },
          { label: "Expenses", value: data.total_expense, prefix: "₹", color: "text-coral" },
          { label: "Savings rate", value: data.savings_rate, suffix: "%" },
        ].map((kpi, i) => (
          <Reveal key={kpi.label} delay={i * 0.05}>
            <Card spotlight>
              <CardTitle>{kpi.label}</CardTitle>
              <CardValue className={kpi.color}>
                <CountUp value={kpi.value} prefix={kpi.prefix} suffix={kpi.suffix} decimals={kpi.suffix ? 1 : 0} />
              </CardValue>
            </Card>
          </Reveal>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Reveal className="lg:col-span-2">
          <Card>
            <CardTitle>Cashflow trend</CardTitle>
            <AreaTrend data={data.monthly_trend} />
          </Card>
        </Reveal>
        <Reveal delay={0.1}>
          <Card className="flex flex-col items-center justify-center">
            <CardTitle>Financial health</CardTitle>
            <RadialScore score={data.health_score} />
          </Card>
        </Reveal>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Reveal>
          <Card>
            <CardTitle>Spending by category</CardTitle>
            <DonutBreakdown data={data.category_breakdown} />
          </Card>
        </Reveal>
        <Reveal delay={0.1}>
          <Card>
            <CardTitle>AI brief</CardTitle>
            <div className="space-y-3 mt-3">
              {data.recommendations.slice(0, 3).map((rec) => (
                <div key={rec.title} className="ai-border rounded-xl p-4 bg-sunken/50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm">{rec.title}</span>
                    <Badge color={rec.priority === "high" ? "coral" : rec.priority === "medium" ? "amber" : "muted"}>
                      {rec.priority}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted">{rec.description}</p>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
      </div>

      <Reveal>
        <Card>
          <CardTitle>Recent activity</CardTitle>
          <div className="mt-3 divide-y divide-border">
            {data.recent_transactions.slice(0, 8).map((txn) => (
              <div key={txn.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <div className="font-medium">{txn.narration}</div>
                  <div className="text-muted text-xs">{txn.category} · {txn.mode}</div>
                </div>
                <span className={`font-mono font-medium ${txn.txn_type === "CREDIT" ? "text-jade" : "text-ink"}`}>
                  {txn.txn_type === "CREDIT" ? "+" : "-"}{formatINR(txn.amount)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </Reveal>
    </div>
  );
}
