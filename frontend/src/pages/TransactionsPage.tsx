import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef } from "react";
import { transactionsApi, type Transaction } from "../lib/api";
import { Card, CardTitle } from "../components/primitives/Card";
import { Input } from "../components/primitives/Input";
import { Button } from "../components/primitives/Button";
import { Reveal } from "../motion/Reveal";
import { formatINR, formatDate } from "../lib/format";

export function TransactionsPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const parentRef = useRef<HTMLDivElement>(null);

  const { data = [] } = useQuery({
    queryKey: ["transactions", category],
    queryFn: async () => (await transactionsApi.list({ limit: 500, category: category || undefined })).data,
  });

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return data.filter(
      (t) =>
        !q ||
        t.narration.toLowerCase().includes(q) ||
        t.category.toLowerCase().includes(q),
    );
  }, [data, search]);

  const categories = useMemo(() => [...new Set(data.map((t) => t.category))], [data]);

  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 8,
  });

  const exportCsv = () => {
    const header = "Date,Narration,Category,Type,Amount,Mode\n";
    const rows = filtered
      .map((t) =>
        `${t.transaction_timestamp},${t.narration},${t.category},${t.txn_type},${t.amount},${t.mode}`,
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "novaa-transactions.csv";
    a.click();
  };

  return (
    <div className="space-y-6">
      <Reveal>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Transactions</h1>
            <p className="text-muted text-sm">{filtered.length} transactions</p>
          </div>
          <Button variant="outline" onClick={exportCsv}>Export CSV</Button>
        </div>
      </Reveal>

      <Reveal>
        <div className="flex gap-3 flex-wrap">
          <Input
            placeholder="Search narrations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-10 rounded-xl border border-border bg-surface px-3 text-sm"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </Reveal>

      <Card>
        <CardTitle>Transaction grid</CardTitle>
        <div ref={parentRef} className="mt-3 h-[500px] overflow-auto">
          <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
            {virtualizer.getVirtualItems().map((item) => {
              const txn = filtered[item.index] as Transaction;
              return (
                <div
                  key={txn.id}
                  className="absolute left-0 right-0 flex items-center justify-between px-2 border-b border-border text-sm"
                  style={{ height: item.size, transform: `translateY(${item.start}px)` }}
                >
                  <div>
                    <div className="font-medium">{txn.narration}</div>
                    <div className="text-xs text-muted">
                      {formatDate(txn.transaction_timestamp)} · {txn.category} · {txn.mode}
                    </div>
                  </div>
                  <span className={`font-mono ${txn.txn_type === "CREDIT" ? "text-jade" : ""}`}>
                    {txn.txn_type === "CREDIT" ? "+" : "-"}{formatINR(txn.amount)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </Card>
    </div>
  );
}
