import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Logo } from "../components/brand/Logo";
import { AuroraBackdrop } from "../components/brand/AuroraBackdrop";
import { SignalGrid } from "../components/brand/SignalGrid";
import { Button } from "../components/primitives/Button";
import { Input } from "../components/primitives/Input";
import { Card } from "../components/primitives/Card";
import { Reveal } from "../motion/Reveal";
import { Stagger, StaggerItem } from "../motion/Stagger";
import { Magnetic } from "../motion/Magnetic";
import { CountUp } from "../motion/CountUp";
import { marketingApi, authApi, dashboardApi } from "../lib/api";
import { useQuery } from "@tanstack/react-query";
import { Shield, BarChart3, Search, Zap } from "lucide-react";

const BANKS = ["HDFC", "ICICI", "SBI", "Axis", "Kotak", "Zerodha", "IDFC", "Yes Bank", "IndusInd", "Federal", "AU Bank", "Bandhan"];

export function LandingPage() {
  const [email, setEmail] = useState("");
  const [joined, setJoined] = useState(false);
  const navigate = useNavigate();

  const { data: waitlist } = useQuery({
    queryKey: ["waitlist"],
    queryFn: async () => (await marketingApi.waitlistCount()).data,
  });

  const joinWaitlist = async (e: React.FormEvent) => {
    e.preventDefault();
    await marketingApi.waitlist(email);
    setJoined(true);
  };

  const tryDemo = async () => {
    const res = await authApi.demoLogin();
    localStorage.setItem("novaa_token", res.data.access_token);
    await dashboardApi.loadMock();
    navigate("/app/overview");
  };

  return (
    <div className="min-h-screen bg-canvas text-ink relative overflow-hidden">
      <AuroraBackdrop />
      <SignalGrid />

      <header className="sticky top-0 z-50 glass border-b border-border">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Logo />
          <nav className="hidden md:flex items-center gap-8 text-sm text-muted">
            <a href="#features" className="hover:text-ink transition">Features</a>
            <a href="#privacy" className="hover:text-ink transition">Privacy</a>
            <a href="#banks" className="hover:text-ink transition">Banks</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login"><Button variant="ghost" size="sm">Sign in</Button></Link>
            <Magnetic><Button size="sm" onClick={() => navigate("/signup")}>Get started</Button></Magnetic>
          </div>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 pt-20 pb-24">
        <Reveal>
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 rounded-full bg-nova/10 text-nova text-xs font-medium px-4 py-1.5 mb-6">
              <Zap size={14} /> RBI Account Aggregator · Live
            </div>
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-[1.1]">
              Your money, in{" "}
              <span className="bg-gradient-to-r from-nova to-aurora bg-clip-text text-transparent">
                full resolution
              </span>
            </h1>
            <p className="text-lg text-muted mt-6 max-w-xl mx-auto">
              NOVAA turns consented bank data into premium financial analytics. Cashflow, spending, AI recall — all in one workspace.
            </p>
            <div className="flex items-center justify-center gap-3 mt-8">
              <Magnetic><Button size="lg" onClick={() => navigate("/signup")}>Start free</Button></Magnetic>
              <Button size="lg" variant="outline" onClick={tryDemo}>Try demo</Button>
            </div>
            <p className="text-xs text-muted mt-4">
              <CountUp value={14800 + (waitlist?.count || 0)} />+ users on waitlist
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <Card className="mt-16 max-w-4xl mx-auto p-0 overflow-hidden" spotlight>
            <div className="bg-sunken px-4 py-2 border-b border-border flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-coral/60" />
              <div className="w-3 h-3 rounded-full bg-amber/60" />
              <div className="w-3 h-3 rounded-full bg-jade/60" />
              <span className="text-xs text-muted ml-2 font-mono">novaa — analytics workspace</span>
            </div>
            <div className="p-6 grid grid-cols-3 gap-4">
              {[
                { label: "Net worth", value: 42000, prefix: "₹" },
                { label: "Savings rate", value: 24.5, suffix: "%" },
                { label: "Health score", value: 78 },
              ].map((kpi) => (
                <div key={kpi.label} className="rounded-xl bg-surface p-4 border border-border">
                  <div className="text-xs text-muted">{kpi.label}</div>
                  <div className="text-xl font-bold font-mono mt-1">
                    <CountUp value={kpi.value} prefix={kpi.prefix} suffix={kpi.suffix} decimals={kpi.suffix ? 1 : 0} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>
      </section>

      <section id="features" className="max-w-6xl mx-auto px-6 py-20">
        <Reveal>
          <h2 className="text-3xl font-bold text-center mb-12">Analytical by design</h2>
        </Reveal>
        <Stagger className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: BarChart3, title: "Cashflow analytics", desc: "Waterfall charts, runway forecast, and spending calendar heatmaps." },
            { icon: Search, title: "Recall search", desc: "Ask your finances anything in plain English. Instant answers from your data." },
            { icon: Shield, title: "RBI AA compliant", desc: "Consent-first data via Account Aggregator. Zero SMS scraping." },
          ].map((f) => (
            <StaggerItem key={f.title}>
              <Card spotlight className="h-full">
                <f.icon className="text-nova mb-3" size={24} />
                <h3 className="font-semibold">{f.title}</h3>
                <p className="text-sm text-muted mt-2">{f.desc}</p>
              </Card>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      <section id="privacy" className="max-w-6xl mx-auto px-6 py-20">
        <Reveal>
          <Card className="p-8 md:p-12">
            <h2 className="text-2xl font-bold mb-4">Privacy architecture</h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-coral font-medium text-sm mb-2">Legacy apps</h3>
                <ul className="text-sm text-muted space-y-2">
                  <li>Read your SMS and OTPs</li>
                  <li>Scrape email statements</li>
                  <li>Store credentials insecurely</li>
                </ul>
              </div>
              <div>
                <h3 className="text-jade font-medium text-sm mb-2">NOVAA via AA</h3>
                <ul className="text-sm text-muted space-y-2">
                  <li>Cryptographically signed bank data</li>
                  <li>You control consent — revoke anytime</li>
                  <li>AES-256 encrypted at rest</li>
                </ul>
              </div>
            </div>
          </Card>
        </Reveal>
      </section>

      <section id="banks" className="max-w-6xl mx-auto px-6 py-20">
        <Reveal>
          <h2 className="text-2xl font-bold text-center mb-8">Supported banks</h2>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {BANKS.map((bank) => (
              <div key={bank} className="glass rounded-xl p-4 text-center text-sm font-medium hover:shadow-glow transition">
                {bank}
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-20">
        <Reveal>
          <Card className="text-center p-12 ai-border">
            <h2 className="text-2xl font-bold">Get early access</h2>
            <p className="text-muted mt-2">Join the waitlist for priority onboarding.</p>
            {joined ? (
              <p className="text-jade mt-6 font-medium">You're on the list!</p>
            ) : (
              <form onSubmit={joinWaitlist} className="flex gap-2 max-w-md mx-auto mt-6">
                <Input type="email" placeholder="you@email.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
                <Button type="submit">Join</Button>
              </form>
            )}
          </Card>
        </Reveal>
      </section>

      <footer className="border-t border-border py-8 text-center text-sm text-muted">
        <Logo showText className="justify-center mb-2" />
        <p>NOVAA — Net-worth Observability via Verified Account Aggregation</p>
        <p className="mt-1">© 2026 NOVAA. Built in India.</p>
      </footer>
    </div>
  );
}
