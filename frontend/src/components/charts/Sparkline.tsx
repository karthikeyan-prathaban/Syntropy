import { Line, LineChart, ResponsiveContainer } from "recharts";

export function Sparkline({ data }: { data: { v: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data}>
        <Line type="monotone" dataKey="v" stroke="#5b5bd6" strokeWidth={1.5} dot={false} animationDuration={600} />
      </LineChart>
    </ResponsiveContainer>
  );
}
