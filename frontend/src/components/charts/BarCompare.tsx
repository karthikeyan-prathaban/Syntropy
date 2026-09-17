import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { month: string; income?: number; expense?: number };

export function BarCompare({ data }: { data: Point[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
        <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
        <Tooltip contentStyle={{ background: "var(--color-surface)", borderRadius: 12, fontSize: 12 }} />
        <Bar dataKey="income" fill="#0fa37f" radius={[4, 4, 0, 0]} animationDuration={800} />
        <Bar dataKey="expense" fill="#f2555a" radius={[4, 4, 0, 0]} animationDuration={800} />
      </BarChart>
    </ResponsiveContainer>
  );
}
