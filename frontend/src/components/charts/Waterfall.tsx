import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { name: string; value: number; fill?: string };

export function Waterfall({ data }: { data: Point[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
        <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
        <Tooltip contentStyle={{ background: "var(--color-surface)", borderRadius: 12, fontSize: 12 }} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} animationDuration={800}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill || (entry.value >= 0 ? "#0fa37f" : "#f2555a")} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
