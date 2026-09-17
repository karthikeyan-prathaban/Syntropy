import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#5b5bd6", "#22b8cf", "#0fa37f", "#f0a028", "#f2555a", "#a855f7", "#ec4899", "#14b8a6"];

export function DonutBreakdown({
  data,
}: {
  data: { category: string; amount: number; percentage: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey="amount"
          nameKey="category"
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={2}
          animationDuration={900}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 12,
            fontSize: 12,
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
