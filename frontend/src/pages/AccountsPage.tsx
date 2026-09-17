import { useQuery } from "@tanstack/react-query";
import { dashboardApi, consentApi } from "../lib/api";
import { Card, CardTitle, CardValue } from "../components/primitives/Card";
import { Button } from "../components/primitives/Button";
import { Badge } from "../components/primitives/Badge";
import { Sparkline } from "../components/charts/Sparkline";
import { Reveal } from "../motion/Reveal";
import { formatINR } from "../lib/format";

export function AccountsPage() {
  const { data, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await dashboardApi.get()).data,
  });

  const linkBank = async () => {
    const res = await consentApi.create();
    const url = res.data.consent_url;
    if (url) window.location.href = url;
  };

  const revoke = async (consentId: string) => {
    await consentApi.revoke(consentId);
    refetch();
  };

  return (
    <div className="space-y-6">
      <Reveal>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Accounts</h1>
            <p className="text-muted text-sm">Linked accounts via RBI Account Aggregator</p>
          </div>
          <Button onClick={linkBank}>Link bank account</Button>
        </div>
      </Reveal>

      <Reveal>
        <Card className="flex items-center justify-between">
          <div>
            <CardTitle>Consent status</CardTitle>
            <CardValue className="text-base capitalize">{data?.consent_status || "Not linked"}</CardValue>
          </div>
          <Badge color={data?.consent_status === "ACTIVE" ? "jade" : "amber"}>
            RBI AA
          </Badge>
        </Card>
      </Reveal>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(data?.accounts || []).map((acc, i) => (
          <Reveal key={acc.id} delay={i * 0.05}>
            <Card spotlight>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle>{acc.account_type}</CardTitle>
                  <div className="text-sm text-muted mt-1">{acc.masked_acc_number}</div>
                  <CardValue>{formatINR(acc.current_balance)}</CardValue>
                </div>
                <Badge color="nova">{acc.currency}</Badge>
              </div>
              <Sparkline data={[{ v: 1 }, { v: 3 }, { v: 2 }, { v: 4 }, { v: acc.current_balance / 10000 }]} />
            </Card>
          </Reveal>
        ))}
        {!(data?.accounts || []).length && (
          <Card className="col-span-full text-center py-12">
            <p className="text-muted">No accounts linked yet. Connect via Account Aggregator to begin.</p>
            <Button className="mt-4" onClick={linkBank}>Start consent journey</Button>
          </Card>
        )}
      </div>

      {data?.consent_status === "ACTIVE" && (
        <Reveal>
          <Card>
            <CardTitle>Manage consent</CardTitle>
            <p className="text-sm text-muted mt-2">Revoke consent to stop data sharing with NOVAA.</p>
            <Button variant="outline" className="mt-3 text-coral border-coral/30" onClick={() => revoke("mock-consent")}>
              Revoke consent
            </Button>
          </Card>
        </Reveal>
      )}
    </div>
  );
}
