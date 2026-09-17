import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { month: string; income?: number; expense?: number; net?: number };

export function AreaTrend({ data }: { data: Point[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0fa37f" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#0fa37f" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f2555a" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#f2555a" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
        <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 12,
            fontSize: 12,
          }}
        />
        <Area type="monotone" dataKey="income" stroke="#0fa37f" fill="url(#incomeGrad)" strokeWidth={2} animationDuration={900} />
        <Area type="monotone" dataKey="expense" stroke="#f2555a" fill="url(#expenseGrad)" strokeWidth={2} animationDuration={900} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
