import { useState } from "react";
import { Card, CardTitle } from "../components/primitives/Card";
import { Input } from "../components/primitives/Input";
import { Button } from "../components/primitives/Button";
import { Reveal } from "../motion/Reveal";
import { streamText } from "../lib/api";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "../lib/api";
import { Badge } from "../components/primitives/Badge";
import { Sparkles } from "lucide-react";

export function InsightsPage() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);

  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await dashboardApi.get()).data,
  });

  const chat = async () => {
    if (!message.trim()) return;
    setLoading(true);
    setReply("");
    await streamText("/insights/chat", { message }, (chunk) => {
      setReply((prev) => prev + chunk);
    });
    setLoading(false);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <Reveal>
        <h1 className="text-2xl font-bold">AI Insights</h1>
        <p className="text-muted text-sm">Your personal financial advisor powered by analytics</p>
      </Reveal>

      <Reveal>
        <div className="space-y-3">
          {(data?.recommendations || []).map((rec) => (
            <Card key={rec.title} className="ai-border">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-nova" />
                <span className="font-medium text-sm">{rec.title}</span>
                <Badge color={rec.priority === "high" ? "coral" : "amber"}>{rec.priority}</Badge>
              </div>
              <p className="text-sm text-muted mt-2">{rec.description}</p>
            </Card>
          ))}
        </div>
      </Reveal>

      <Reveal>
        <Card spotlight>
          <CardTitle>Chat with NOVAA</CardTitle>
          <div className="flex gap-2 mt-3">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="How can I improve my savings?"
              onKeyDown={(e) => e.key === "Enter" && chat()}
            />
            <Button onClick={chat} disabled={loading}>Ask</Button>
          </div>
          {(reply || loading) && (
            <p className="mt-4 text-sm leading-relaxed bg-sunken rounded-xl p-4">
              {reply}
              {loading && <span className="inline-block w-2 h-4 bg-nova animate-pulse ml-0.5" />}
            </p>
          )}
        </Card>
      </Reveal>
    </div>
  );
}
