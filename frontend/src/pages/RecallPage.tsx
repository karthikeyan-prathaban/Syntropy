import { useState } from "react";
import { Card, CardTitle } from "../components/primitives/Card";
import { Input } from "../components/primitives/Input";
import { Button } from "../components/primitives/Button";
import { Reveal } from "../motion/Reveal";
import { streamText } from "../lib/api";
import { Search } from "lucide-react";

const PRESETS = [
  "How much did I spend on food?",
  "What's my savings rate?",
  "Show my top spending category",
  "Find all Swiggy transactions",
];

export function RecallPage() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const ask = async (q: string) => {
    setQuery(q);
    setLoading(true);
    setAnswer("");
    await streamText("/recall/query", { query: q }, (chunk) => {
      setAnswer((prev) => prev + chunk);
    });
    setLoading(false);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <Reveal>
        <h1 className="text-2xl font-bold">Recall</h1>
        <p className="text-muted text-sm">Natural-language search across your financial data</p>
      </Reveal>

      <Reveal>
        <Card className="ai-border">
          <CardTitle>Ask anything</CardTitle>
          <div className="flex gap-2 mt-3">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="How much did I spend on dining last month?"
              onKeyDown={(e) => e.key === "Enter" && ask(query)}
            />
            <Button onClick={() => ask(query)} disabled={loading}>
              <Search size={16} />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {PRESETS.map((p) => (
              <button
                key={p}
                onClick={() => ask(p)}
                className="text-xs px-3 py-1.5 rounded-full bg-sunken text-muted hover:text-nova hover:bg-nova/10 transition"
              >
                {p}
              </button>
            ))}
          </div>
        </Card>
      </Reveal>

      {(answer || loading) && (
        <Reveal>
          <Card spotlight>
            <CardTitle>Answer</CardTitle>
            <p className="mt-3 text-sm leading-relaxed">
              {answer}
              {loading && <span className="inline-block w-2 h-4 bg-nova animate-pulse ml-0.5" />}
            </p>
          </Card>
        </Reveal>
      )}
    </div>
  );
}
