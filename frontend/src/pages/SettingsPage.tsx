import { useQuery } from "@tanstack/react-query";
import { api, dashboardApi } from "../lib/api";
import { Card, CardTitle } from "../components/primitives/Card";
import { Button } from "../components/primitives/Button";
import { Reveal } from "../motion/Reveal";
import { useTheme } from "../app/ThemeProvider";

export function SettingsPage() {
  const { theme, toggle } = useTheme();
  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await dashboardApi.get()).data,
  });

  const purgeData = async () => {
    if (!confirm("Delete all financial data? This cannot be undone.")) return;
    await api.delete("/me/data");
    window.location.reload();
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <Reveal>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted text-sm">Profile, privacy, and preferences</p>
      </Reveal>

      <Reveal>
        <Card>
          <CardTitle>Profile</CardTitle>
          <div className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-muted">Name</span><span>{data?.user.name}</span></div>
            <div className="flex justify-between"><span className="text-muted">Mobile</span><span>{data?.user.mobile}</span></div>
            <div className="flex justify-between"><span className="text-muted">Email</span><span>{data?.user.email || "—"}</span></div>
          </div>
        </Card>
      </Reveal>

      <Reveal delay={0.05}>
        <Card>
          <CardTitle>Appearance</CardTitle>
          <p className="text-sm text-muted mt-2">Current theme: {theme}</p>
          <Button variant="outline" className="mt-3" onClick={toggle}>
            Switch to {theme === "light" ? "dark" : "light"} mode
          </Button>
        </Card>
      </Reveal>

      <Reveal delay={0.1}>
        <Card>
          <CardTitle>Data & privacy</CardTitle>
          <p className="text-sm text-muted mt-2">
            NOVAA uses RBI Account Aggregator. Your data is never sold or shared without consent.
          </p>
          <Button variant="outline" className="mt-3 text-coral border-coral/30" onClick={purgeData}>
            Purge all financial data
          </Button>
        </Card>
      </Reveal>
    </div>
  );
}
