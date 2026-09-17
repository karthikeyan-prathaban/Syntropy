import { formatINR } from "../../lib/format";

type Day = { date: string; amount: number; count: number };

export function Heatmap({ data }: { data: Day[] }) {
  const max = Math.max(...data.map((d) => d.amount), 1);
  return (
    <div className="grid grid-cols-7 gap-1">
      {data.map((d) => (
        <div
          key={d.date}
          className="aspect-square rounded-md flex items-center justify-center text-[9px] font-mono"
          style={{
            backgroundColor: `color-mix(in srgb, var(--color-nova) ${Math.round((d.amount / max) * 80 + 10)}%, transparent)`,
          }}
          title={`${d.date}: ${formatINR(d.amount)} (${d.count} txns)`}
        >
          {new Date(d.date).getDate()}
        </div>
      ))}
    </div>
  );
}
