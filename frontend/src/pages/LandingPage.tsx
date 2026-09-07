import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { demoLogin, getWaitlistCount, joinWaitlist, loadMockData } from "../api/client";
import { Analytics, getStoredUTMs } from "../utils/analytics";

// ── Mock Data for Live Interactive Simulator ─────────────────────────────────

interface MockBank {
  id: string;
  name: string;
  shortName: string;
  logo: string;
  accNumber: string;
  balance: number;
  type: "Savings" | "Current" | "Investments";
}

interface MockTransaction {
  id: string;
  bankId: string;
  merchant: string;
  category: string;
  amount: number;
  type: "DEBIT" | "CREDIT";
  date: string;
  time: string;
  rawNarration: string;
  icon: string;
}

const MOCK_BANKS: MockBank[] = [
  { id: "hdfc", name: "HDFC Bank", shortName: "HDFC", logo: "🏦", accNumber: "•••• 4920", balance: 342850, type: "Savings" },
  { id: "icici", name: "ICICI Bank", shortName: "ICICI", logo: "🏛️", accNumber: "•••• 8104", balance: 194500, type: "Current" },
  { id: "sbi", name: "State Bank of India", shortName: "SBI", logo: "🇮🇳", accNumber: "•••• 2291", balance: 88200, type: "Savings" },
  { id: "zerodha", name: "Zerodha & Groww", shortName: "Investments", logo: "📈", accNumber: "•••• 7712", balance: 814000, type: "Investments" },
];

const MOCK_TRANSACTIONS: MockTransaction[] = [
  {
    id: "tx1",
    bankId: "hdfc",
    merchant: "Swiggy Gourmet",
    category: "Food & Dining",
    amount: 840,
    type: "DEBIT",
    date: "Today",
    time: "1:15 PM",
    rawNarration: "UPI/DR/4291039401/SWIGGY_BLR/HDFC000001",
    icon: "🍔",
  },
  {
    id: "tx2",
    bankId: "icici",
    merchant: "Stripe Payout (Consulting)",
    category: "Income",
    amount: 125000,
    type: "CREDIT",
    date: "Today",
    time: "10:30 AM",
    rawNarration: "NEFT/CR/STRPIND092301/STRIPE_CONSULTING",
    icon: "💼",
  },
  {
    id: "tx3",
    bankId: "hdfc",
    merchant: "Amazon India",
    category: "Shopping",
    amount: 3499,
    type: "DEBIT",
    date: "Yesterday",
    time: "6:45 PM",
    rawNarration: "UPI/DR/4290119283/AMZN_MKT_IN/YESB000001",
    icon: "📦",
  },
  {
    id: "tx4",
    bankId: "zerodha",
    merchant: "Nifty 50 Index Fund SIP",
    category: "Investments",
    amount: 25000,
    type: "DEBIT",
    date: "Sep 05",
    time: "9:00 AM",
    rawNarration: "ACH/DR/ZRDHMF002910/AUTOPAY_NIFTY50",
    icon: "📊",
  },
  {
    id: "tx5",
    bankId: "hdfc",
    merchant: "Netflix Premium 4K",
    category: "Subscriptions",
    amount: 649,
    type: "DEBIT",
    date: "Sep 04",
    time: "12:00 AM",
    rawNarration: "E-MANDATE/DR/NFLX992019/AUTODEBIT",
    icon: "🎬",
  },
  {
    id: "tx6",
    bankId: "sbi",
    merchant: "Quarterly Fixed Deposit Interest",
    category: "Income",
    amount: 4210,
    type: "CREDIT",
    date: "Sep 01",
    time: "3:30 AM",
    rawNarration: "INT/CR/FD0098230192/SBI_INTEREST",
    icon: "💰",
  },
  {
    id: "tx7",
    bankId: "icici",
    merchant: "Google Workspace & GCP",
    category: "Utilities & Cloud",
    amount: 4890,
    type: "DEBIT",
    date: "Aug 29",
    time: "11:20 AM",
    rawNarration: "POS/DR/GOOG_CLOUD_IN/ICIC000002",
    icon: "☁️",
  },
  {
    id: "tx8",
    bankId: "hdfc",
    merchant: "Uber Premier",
    category: "Travel & Commute",
    amount: 480,
    type: "DEBIT",
    date: "Aug 28",
    time: "8:10 PM",
    rawNarration: "UPI/DR/4289100234/UBER_INDIA/PYTM000001",
    icon: "🚗",
  },
];

const SUPPORTED_BANKS = [
  { name: "HDFC Bank", uptime: "99.9%", status: "live" },
  { name: "State Bank of India", uptime: "99.4%", status: "live" },
  { name: "ICICI Bank", uptime: "99.8%", status: "live" },
  { name: "Axis Bank", uptime: "99.7%", status: "live" },
  { name: "Kotak Mahindra", uptime: "99.9%", status: "live" },
  { name: "IndusInd Bank", uptime: "99.6%", status: "live" },
  { name: "Bank of Baroda", uptime: "99.3%", status: "live" },
  { name: "Punjab National Bank", uptime: "99.1%", status: "live" },
  { name: "IDFC FIRST Bank", uptime: "99.9%", status: "live" },
  { name: "Federal Bank", uptime: "99.8%", status: "live" },
  { name: "Zerodha Broking", uptime: "99.9%", status: "live" },
  { name: "Groww", uptime: "99.8%", status: "live" },
];

function fmtINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function LandingPage() {
  const navigate = useNavigate();

  // Waitlist state
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistLoading, setWaitlistLoading] = useState(false);
  const [waitlistSuccess, setWaitlistSuccess] = useState<number | null>(null);
  const [waitlistError, setWaitlistError] = useState("");
  const [waitlistCount, setWaitlistCount] = useState(14820);

  // Demo simulator interactive states
  const [selectedBank, setSelectedBank] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [demoLaunching, setDemoLaunching] = useState(false);

  // AI Prompt simulator
  const [activePromptIndex, setActivePromptIndex] = useState(0);

  // Bank statement cleaner teaser state
  const [cleanedView, setCleanedView] = useState<"clean" | "raw">("clean");
  const [copiedNotification, setCopiedNotification] = useState("");

  useEffect(() => {
    Analytics.pageView("Landing Page");
    getWaitlistCount()
      .then((res) => {
        if (res.count && res.count > 0) {
          setWaitlistCount(14800 + res.count);
        }
      })
      .catch(() => {});
  }, []);

  // Filtered simulator transactions
  const filteredTransactions = useMemo(() => {
    return MOCK_TRANSACTIONS.filter((tx) => {
      if (selectedBank !== "all" && tx.bankId !== selectedBank) return false;
      if (selectedCategory !== "All" && tx.category !== selectedCategory) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          tx.merchant.toLowerCase().includes(q) ||
          tx.category.toLowerCase().includes(q) ||
          tx.rawNarration.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [selectedBank, selectedCategory, searchQuery]);

  // Total balance computation for simulator
  const currentDisplayedBalance = useMemo(() => {
    if (selectedBank === "all") {
      return MOCK_BANKS.reduce((acc, b) => acc + b.balance, 0);
    }
    const bank = MOCK_BANKS.find((b) => b.id === selectedBank);
    return bank ? bank.balance : 0;
  }, [selectedBank]);

  // Categories list
  const categories = ["All", "Food & Dining", "Income", "Investments", "Shopping", "Subscriptions"];

  // AI Prompts
  const aiPrompts = [
    {
      q: "Where did my money go this month?",
      a: "Out of ₹1,48,500 total spends, Food & Dining was ₹34,200 (23% of total). That is 18% higher than your 3-month average, driven primarily by weekend Swiggy orders.",
      tag: "Spending Breakdown",
    },
    {
      q: "Find recurring subscriptions I might not need",
      a: "Detected 4 active recurring autopays: Netflix (₹649/mo), Spotify (₹119/mo), Google Storage (₹130/mo), and Gym Membership (₹2,500/mo). Annualized leakage: ₹40,776.",
      tag: "Leak Detection",
    },
    {
      q: "Can I afford a ₹1,20,000 international flight next week?",
      a: "Yes. You have ₹3.42L liquid cash in HDFC and ₹88.2K emergency fund in SBI. Post-booking, your liquid reserve remains 3.2x your monthly fixed obligations (₹42,000 safe buffer).",
      tag: "Affordability Check",
    },
    {
      q: "How much did I save under Section 80C & NPS?",
      a: "You have utilized ₹1.25L of your ₹1.5L 80C limit via ELSS and EPF. You need ₹25,000 more before March 31 to claim full ₹46,800 tax rebate under the Old Regime.",
      tag: "Tax Optimization",
    },
  ];

  async function handleWaitlistSubmit(e: FormEvent) {
    e.preventDefault();
    if (!waitlistEmail || !waitlistEmail.includes("@")) {
      setWaitlistError("Please enter a valid email address.");
      return;
    }

    setWaitlistLoading(true);
    setWaitlistError("");
    try {
      const utms = getStoredUTMs();
      const res = await joinWaitlist({
        email: waitlistEmail,
        source: "landing_hero",
        utm: utms as any,
      });
      const pos = res.position || waitlistCount + 1;
      setWaitlistSuccess(pos);
      setWaitlistCount((c) => c + 1);
      Analytics.waitlistJoined(waitlistEmail, pos);
    } catch (err: any) {
      setWaitlistError(err?.message || "Could not join waitlist. Please try again.");
    } finally {
      setWaitlistLoading(false);
    }
  }

  async function handleLaunchFullDemo() {
    setDemoLaunching(true);
    Analytics.demoInteracted("launch_full_app");
    try {
      const res = await demoLogin("Karthik", "9876543210");
      localStorage.setItem("syntropy_token", res.access_token);
      localStorage.setItem("syntropy_user", JSON.stringify(res.user));
      localStorage.setItem("syntropy_user_id", String(res.user.id));
      localStorage.setItem("syntropy_user_name", res.user.name);
      await loadMockData(res.user.id);
      navigate("/dashboard");
    } catch {
      navigate("/login");
    } finally {
      setDemoLaunching(false);
    }
  }

  function handleCopySnippet(text: string) {
    navigator.clipboard.writeText(text);
    setCopiedNotification("Copied to clipboard!");
    setTimeout(() => setCopiedNotification(""), 2500);
  }

  return (
    <div style={{ background: "#060d1a", minHeight: "100vh", color: "#f8fafc", overflowX: "hidden" }}>
      {/* ── Sticky Top Navigation ─────────────────────────────────────────── */}
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 90,
          background: "rgba(6, 13, 26, 0.82)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
          padding: "14px 24px",
        }}
      >
        <div style={{ maxWidth: "1280px", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          {/* Logo & Status */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "8px" }}>
              <span className="logo-mark grad-text" style={{ fontSize: "1.45rem", fontWeight: 800 }}>✦ Syntropy</span>
            </Link>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "0.72rem",
                padding: "3px 8px",
                borderRadius: "99px",
                background: "rgba(16, 185, 129, 0.12)",
                color: "#34d399",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                fontWeight: 600,
              }}
            >
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981", boxShadow: "0 0 8px #10b981" }} />
              RBI AA Rails Live
            </span>
          </div>

          {/* Nav Links */}
          <div style={{ display: "none", alignItems: "center", gap: "24px" }} className="desktop-links">
            <a href="#simulator" style={{ color: "#94a3b8", textDecoration: "none", fontSize: "0.9rem", fontWeight: 500 }}>Live Demo</a>
            <a href="#privacy" style={{ color: "#94a3b8", textDecoration: "none", fontSize: "0.9rem", fontWeight: 500 }}>No SMS Scraping</a>
            <a href="#cleaner" style={{ color: "#94a3b8", textDecoration: "none", fontSize: "0.9rem", fontWeight: 500 }}>Clean Statements</a>
            <a href="#ai" style={{ color: "#94a3b8", textDecoration: "none", fontSize: "0.9rem", fontWeight: 500 }}>AI Intelligence</a>
            <a href="#banks" style={{ color: "#94a3b8", textDecoration: "none", fontSize: "0.9rem", fontWeight: 500 }}>40+ Banks</a>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button
              onClick={() => { Analytics.ctaClicked("sign_in_nav", "header"); navigate("/login"); }}
              style={{
                background: "transparent",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                color: "#e2e8f0",
                padding: "7px 16px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              Sign In
            </button>
            <button
              onClick={handleLaunchFullDemo}
              disabled={demoLaunching}
              style={{
                background: "linear-gradient(135deg, #10b981 0%, #06b6d4 100%)",
                border: "none",
                color: "#060d1a",
                fontWeight: 700,
                padding: "8px 18px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                cursor: "pointer",
                boxShadow: "0 0 20px rgba(16, 185, 129, 0.35)",
              }}
            >
              {demoLaunching ? "Launching..." : "Launch App ⚡"}
            </button>
          </div>
        </div>
      </nav>

      {/* ── Notification Toast ────────────────────────────────────────────── */}
      {copiedNotification && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 999,
            background: "#10b981",
            color: "#060d1a",
            padding: "10px 18px",
            borderRadius: "8px",
            fontWeight: 700,
            fontSize: "0.85rem",
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
          }}
        >
          ✓ {copiedNotification}
        </div>
      )}

      {/* ── Hero Section ─────────────────────────────────────────────────── */}
      <header
        style={{
          position: "relative",
          padding: "72px 24px 50px",
          maxWidth: "1280px",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        {/* Background Ambient Glow */}
        <div
          style={{
            position: "absolute",
            top: "20%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "650px",
            height: "350px",
            background: "radial-gradient(circle, rgba(16, 185, 129, 0.12) 0%, rgba(6, 182, 212, 0.08) 40%, transparent 70%)",
            filter: "blur(60px)",
            pointerEvents: "none",
            zIndex: 0,
          }}
        />

        <div style={{ position: "relative", zIndex: 1 }}>
          {/* Regulatory Trust Pill */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 14px",
              borderRadius: "99px",
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "#94a3b8",
              marginBottom: "24px",
            }}
          >
            <span style={{ color: "#10b981" }}>✦</span>
            <span>INDIA&apos;S OFFICIAL RBI ACCOUNT AGGREGATOR RAILS</span>
            <span style={{ color: "rgba(255,255,255,0.2)" }}>•</span>
            <span style={{ color: "#34d399" }}>NO PASSWORDS REQUIRED</span>
          </div>

          {/* Headline */}
          <h1
            style={{
              fontSize: "clamp(2.5rem, 6vw, 4.4rem)",
              fontWeight: 900,
              letterSpacing: "-0.04em",
              lineHeight: 1.08,
              marginBottom: "20px",
            }}
          >
            Your Entire Financial Life.<br />
            <span className="grad-text">Painfully Clear.</span>
          </h1>

          {/* Subtitle */}
          <p
            style={{
              fontSize: "clamp(1.05rem, 2vw, 1.25rem)",
              color: "#94a3b8",
              maxWidth: "760px",
              margin: "0 auto 36px",
              lineHeight: 1.6,
            }}
          >
            Syntropy securely unifies your bank accounts, fixed deposits, and mutual funds through India&apos;s
            official RBI Account Aggregator framework. <strong style={{ color: "#f8fafc" }}>No SMS scraping. No reading your Gmail. No selling your data.</strong>
          </p>

          {/* CTAs */}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "14px", marginBottom: "32px" }}>
            <button
              onClick={handleLaunchFullDemo}
              style={{
                background: "linear-gradient(135deg, #10b981 0%, #06b6d4 100%)",
                border: "none",
                color: "#060d1a",
                fontWeight: 800,
                fontSize: "1rem",
                padding: "14px 28px",
                borderRadius: "12px",
                cursor: "pointer",
                boxShadow: "0 0 30px rgba(16, 185, 129, 0.4)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                transition: "transform 0.2s ease",
              }}
            >
              <span>Explore Live Dashboard</span>
              <span>⚡</span>
            </button>

            <button
              onClick={() => {
                Analytics.ctaClicked("connect_bank_hero", "hero");
                navigate("/login");
              }}
              style={{
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "#f8fafc",
                fontWeight: 600,
                fontSize: "1rem",
                padding: "14px 26px",
                borderRadius: "12px",
                cursor: "pointer",
                backdropFilter: "blur(10px)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span>Connect Real Bank (Setu AA)</span>
              <span>🏦</span>
            </button>
          </div>

          {/* Waitlist Quick Form */}
          <form
            onSubmit={handleWaitlistSubmit}
            style={{
              maxWidth: "480px",
              margin: "0 auto 28px",
              display: "flex",
              gap: "8px",
              background: "rgba(13, 24, 41, 0.8)",
              padding: "6px",
              borderRadius: "12px",
              border: "1px solid rgba(255, 255, 255, 0.08)",
            }}
          >
            <input
              type="email"
              placeholder="Enter your email for early VIP access..."
              value={waitlistEmail}
              onChange={(e) => setWaitlistEmail(e.target.value)}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                padding: "10px 14px",
                color: "#f8fafc",
                fontSize: "0.9rem",
              }}
            />
            <button
              type="submit"
              disabled={waitlistLoading}
              style={{
                background: "rgba(255, 255, 255, 0.1)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "#fff",
                fontWeight: 600,
                fontSize: "0.85rem",
                padding: "10px 18px",
                borderRadius: "8px",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {waitlistLoading ? "Reserving..." : "Join Waitlist"}
            </button>
          </form>

          {waitlistSuccess && (
            <div style={{ color: "#34d399", fontSize: "0.9rem", fontWeight: 600, marginBottom: "20px" }}>
              🎉 You&apos;re spot #{waitlistSuccess.toLocaleString()} in line! We&apos;ll notify you when VIP spots open.
            </div>
          )}
          {waitlistError && (
            <div style={{ color: "#ef4444", fontSize: "0.85rem", marginBottom: "20px" }}>{waitlistError}</div>
          )}

          {/* Social Proof Metric */}
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "20px", color: "#64748b", fontSize: "0.82rem" }}>
            <span>✓ {waitlistCount.toLocaleString()}+ on the waitlist</span>
            <span>•</span>
            <span>✓ 40+ Banks Supported</span>
            <span>•</span>
            <span>✓ 256-Bit TLS Hardware Encryption</span>
          </div>
        </div>
      </header>

      {/* ── Live Interactive Financial Terminal ───────────────────────────── */}
      <section
        id="simulator"
        style={{
          maxWidth: "1280px",
          margin: "20px auto 100px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            background: "linear-gradient(180deg, rgba(13, 24, 41, 0.9) 0%, rgba(8, 16, 28, 0.95) 100%)",
            borderRadius: "24px",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 20px 80px rgba(0, 0, 0, 0.6), 0 0 50px rgba(16, 185, 129, 0.05)",
            overflow: "hidden",
          }}
        >
          {/* Terminal Header Bar */}
          <div
            style={{
              padding: "16px 24px",
              borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "rgba(255, 255, 255, 0.02)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{ display: "flex", gap: "6px" }}>
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#ef4444" }} />
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#f59e0b" }} />
                <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#10b981" }} />
              </div>
              <span style={{ fontSize: "0.85rem", color: "#64748b", fontFamily: "monospace", marginLeft: "8px" }}>
                syntropy-terminal // aggregated_financial_stream.live
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "#34d399",
                  background: "rgba(16, 185, 129, 0.1)",
                  padding: "4px 10px",
                  borderRadius: "99px",
                  fontWeight: 600,
                }}
              >
                ● Interactive Simulator Active
              </span>
              <button
                onClick={handleLaunchFullDemo}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#e2e8f0",
                  padding: "4px 12px",
                  borderRadius: "6px",
                  fontSize: "0.78rem",
                  cursor: "pointer",
                }}
              >
                Expand Full Screen ↗
              </button>
            </div>
          </div>

          {/* Simulator Body */}
          <div style={{ padding: "28px" }}>
            {/* Top Stat Row: Net Worth + Account Tabs */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "24px",
                alignItems: "center",
                marginBottom: "28px",
              }}
            >
              {/* Aggregated Balance Card */}
              <div
                style={{
                  background: "rgba(255, 255, 255, 0.03)",
                  padding: "20px 24px",
                  borderRadius: "16px",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <div style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
                  {selectedBank === "all" ? "Unified Net Worth" : `${MOCK_BANKS.find((b) => b.id === selectedBank)?.name} Balance`}
                </div>
                <div style={{ fontSize: "2.4rem", fontWeight: 900, letterSpacing: "-0.03em", margin: "6px 0", color: "#f8fafc" }}>
                  {fmtINR(currentDisplayedBalance)}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.82rem", color: "#34d399", fontWeight: 600 }}>
                  <span>↑ +18.4% this financial year</span>
                  <span style={{ color: "#64748b" }}>•</span>
                  <span style={{ color: "#94a3b8" }}>Updated just now via AA</span>
                </div>
              </div>

              {/* Bank Selector Switcher */}
              <div>
                <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginBottom: "10px", fontWeight: 600 }}>
                  SELECT ACCOUNT TO FILTER LIVE TRANSACTIONS:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  <button
                    onClick={() => { setSelectedBank("all"); Analytics.bankSwitched("All Banks"); }}
                    style={{
                      background: selectedBank === "all" ? "rgba(16, 185, 129, 0.2)" : "rgba(255, 255, 255, 0.04)",
                      border: `1px solid ${selectedBank === "all" ? "#10b981" : "rgba(255, 255, 255, 0.08)"}`,
                      color: selectedBank === "all" ? "#34d399" : "#cbd5e1",
                      padding: "8px 14px",
                      borderRadius: "10px",
                      fontSize: "0.85rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    🌐 All Accounts ({fmtINR(1439550)})
                  </button>
                  {MOCK_BANKS.map((b) => (
                    <button
                      key={b.id}
                      onClick={() => { setSelectedBank(b.id); Analytics.bankSwitched(b.name); }}
                      style={{
                        background: selectedBank === b.id ? "rgba(16, 185, 129, 0.2)" : "rgba(255, 255, 255, 0.04)",
                        border: `1px solid ${selectedBank === b.id ? "#10b981" : "rgba(255, 255, 255, 0.08)"}`,
                        color: selectedBank === b.id ? "#34d399" : "#cbd5e1",
                        padding: "8px 14px",
                        borderRadius: "10px",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <span>{b.logo}</span>
                      <span>{b.shortName}</span>
                      <span style={{ opacity: 0.65, fontSize: "0.78rem" }}>{fmtINR(b.balance)}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Filter Bar: Live Search & Category Pills */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "16px",
                padding: "16px 0",
                borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
                marginBottom: "20px",
              }}
            >
              {/* Category Pills */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => { setSelectedCategory(cat); Analytics.tagClicked(cat); }}
                    style={{
                      background: selectedCategory === cat ? "rgba(255, 255, 255, 0.15)" : "transparent",
                      border: "none",
                      color: selectedCategory === cat ? "#fff" : "#94a3b8",
                      padding: "6px 12px",
                      borderRadius: "6px",
                      fontSize: "0.82rem",
                      fontWeight: selectedCategory === cat ? 700 : 500,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Search Bar */}
              <div style={{ position: "relative", minWidth: "240px" }}>
                <input
                  type="text"
                  placeholder="Search merchant, tag, or UPI ref..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    if (e.target.value.length > 2) Analytics.searchQueried(e.target.value);
                  }}
                  style={{
                    width: "100%",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    padding: "8px 12px 8px 32px",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "0.82rem",
                    outline: "none",
                  }}
                />
                <span style={{ position: "absolute", left: "10px", top: "8px", color: "#64748b", fontSize: "0.82rem" }}>
                  🔍
                </span>
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    style={{
                      position: "absolute",
                      right: "8px",
                      top: "6px",
                      background: "none",
                      border: "none",
                      color: "#94a3b8",
                      cursor: "pointer",
                      fontSize: "0.75rem",
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>

            {/* Live Transaction Stream Table */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {filteredTransactions.length === 0 ? (
                <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748b" }}>
                  No transactions match &quot;{searchQuery}&quot; in {selectedCategory}.
                </div>
              ) : (
                filteredTransactions.map((tx) => (
                  <div
                    key={tx.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "14px 18px",
                      background: "rgba(255, 255, 255, 0.02)",
                      borderRadius: "12px",
                      border: "1px solid rgba(255, 255, 255, 0.04)",
                      transition: "background 0.2s ease, transform 0.2s ease",
                    }}
                  >
                    {/* Left: Icon & Merchant */}
                    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                      <div
                        style={{
                          width: "42px",
                          height: "42px",
                          borderRadius: "10px",
                          background: "rgba(255, 255, 255, 0.06)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "1.2rem",
                        }}
                      >
                        {tx.icon}
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: "0.92rem", color: "#f8fafc" }}>
                          {tx.merchant}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>
                          <span style={{ color: "#94a3b8" }}>{tx.category}</span>
                          <span>•</span>
                          <span>{tx.date}, {tx.time}</span>
                          <span>•</span>
                          <span style={{ fontFamily: "monospace", opacity: 0.6 }}>{MOCK_BANKS.find((b) => b.id === tx.bankId)?.shortName}</span>
                        </div>
                      </div>
                    </div>

                    {/* Right: Amount & Narration pill */}
                    <div style={{ textAlign: "right" }}>
                      <div
                        style={{
                          fontWeight: 700,
                          fontSize: "1rem",
                          color: tx.type === "CREDIT" ? "#34d399" : "#f8fafc",
                        }}
                      >
                        {tx.type === "CREDIT" ? "+" : "-"}{fmtINR(tx.amount)}
                      </div>
                      <div
                        style={{
                          fontSize: "0.7rem",
                          fontFamily: "monospace",
                          color: "#64748b",
                          maxWidth: "180px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          marginTop: "2px",
                        }}
                        title={tx.rawNarration}
                      >
                        {tx.rawNarration}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* AI Insight Highlight Banner */}
            <div
              style={{
                marginTop: "24px",
                padding: "16px 20px",
                borderRadius: "14px",
                background: "linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.05) 100%)",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "16px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ fontSize: "1.4rem" }}>💡</span>
                <span style={{ fontSize: "0.85rem", color: "#cbd5e1" }}>
                  <strong style={{ color: "#34d399" }}>Syntropy AI Co-Pilot:</strong> You have an excess cash surplus of <strong>₹62,000</strong> in your HDFC account. Moving this to a liquid fund before the 15th will yield an estimated <strong>₹4,300/yr</strong> additional returns.
                </span>
              </div>
              <button
                onClick={handleLaunchFullDemo}
                style={{
                  background: "#10b981",
                  border: "none",
                  color: "#060d1a",
                  padding: "8px 16px",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "0.8rem",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                Act on Insight →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Feature 1: Why Not SMS Scraping (The Syntropy vs Legacy Matrix) ── */}
      <section
        id="privacy"
        style={{
          maxWidth: "1280px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "700px", margin: "0 auto 50px" }}>
          <span
            style={{
              color: "#34d399",
              fontSize: "0.82rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            ARCHITECTURE MATTERS
          </span>
          <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 800, margin: "12px 0", letterSpacing: "-0.03em" }}>
            Stop letting apps read your private SMS and Gmail.
          </h2>
          <p style={{ color: "#94a3b8", fontSize: "1.05rem", lineHeight: 1.6 }}>
            Legacy Indian expense trackers read your personal messages, OTPs, and sell your transaction data to credit card brokers. Syntropy uses the RBI-regulated Account Aggregator pipe.
          </p>
        </div>

        {/* Side by Side Comparison Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "24px",
          }}
        >
          {/* Old Way */}
          <div
            style={{
              background: "rgba(239, 68, 68, 0.03)",
              border: "1px solid rgba(239, 68, 68, 0.15)",
              borderRadius: "20px",
              padding: "32px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
              <span style={{ fontSize: "1.5rem" }}>❌</span>
              <h3 style={{ fontSize: "1.25rem", color: "#f87171" }}>The Old Way (SMS & Gmail Scraping)</h3>
            </div>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "14px", color: "#94a3b8", fontSize: "0.92rem" }}>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Requires permission to read every private SMS and OTP on your phone.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Asks you to link your primary Google account so they can scrape receipts.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Fragile regex: misses bank transfers, cash withdrawals, and UPI autopays.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Business model depends on spamming you with unwanted personal loans & cards.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Impossible to revoke data once stored on their marketing databases.</span>
              </li>
            </ul>
          </div>

          {/* Syntropy Way */}
          <div
            style={{
              background: "linear-gradient(145deg, rgba(16, 185, 129, 0.08) 0%, rgba(6, 182, 212, 0.04) 100%)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              borderRadius: "20px",
              padding: "32px",
              boxShadow: "0 10px 40px rgba(16, 185, 129, 0.08)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
              <span style={{ fontSize: "1.5rem" }}>✅</span>
              <h3 style={{ fontSize: "1.25rem", color: "#34d399" }}>The Syntropy Way (RBI Account Aggregator)</h3>
            </div>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "14px", color: "#cbd5e1", fontSize: "0.92rem" }}>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ color: "#10b981", fontWeight: 700 }}>✓</span> <span><strong>Zero SMS access.</strong> Direct encrypted data stream directly from your bank.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ color: "#10b981", fontWeight: 700 }}>✓</span> <span><strong>Zero email reading.</strong> No Google OAuth permissions or inbox scraping.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ color: "#10b981", fontWeight: 700 }}>✓</span> <span><strong>100% accurate financial statements</strong> cryptographically signed by your bank.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ color: "#10b981", fontWeight: 700 }}>✓</span> <span><strong>Zero advertisements or loan spam.</strong> Your financial data is never sold.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ color: "#10b981", fontWeight: 700 }}>✓</span> <span><strong>One-click consent revocation</strong> anytime directly through the RBI AA registry.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── Feature 2: Bank Statement Cleaner (Fold Money killer feature, made interactive) ── */}
      <section
        id="cleaner"
        style={{
          maxWidth: "1280px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            background: "rgba(13, 24, 41, 0.6)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "24px",
            padding: "48px 36px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "40px",
            alignItems: "center",
          }}
        >
          {/* Left Text */}
          <div>
            <span style={{ color: "#06b6d4", fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              CLEAN DATA INFRASTRUCTURE
            </span>
            <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", fontWeight: 800, margin: "14px 0", letterSpacing: "-0.03em" }}>
              Never visit your bank&apos;s slow portal or crack password PDFs again.
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "1rem", lineHeight: 1.6, marginBottom: "24px" }}>
              Bank net banking portals look like they were built in 2004. Password-protected PDFs constantly break in Excel. Syntropy automatically normalizes cryptic UPI strings into clean merchant names, categories, and audit-ready tax exports.
            </p>

            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <button
                onClick={() => {
                  setCleanedView("clean");
                  Analytics.statementCleanedTested("HDFC", "clean");
                }}
                style={{
                  background: cleanedView === "clean" ? "#10b981" : "rgba(255,255,255,0.06)",
                  border: "none",
                  color: cleanedView === "clean" ? "#060d1a" : "#fff",
                  padding: "9px 16px",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                }}
              >
                View Syntropy Clean View
              </button>
              <button
                onClick={() => {
                  setCleanedView("raw");
                  Analytics.statementCleanedTested("HDFC", "raw");
                }}
                style={{
                  background: cleanedView === "raw" ? "#ef4444" : "rgba(255,255,255,0.06)",
                  border: "none",
                  color: "#fff",
                  padding: "9px 16px",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                }}
              >
                View Raw Bank PDF String
              </button>
            </div>
          </div>

          {/* Right Interactive Card */}
          <div
            style={{
              background: "rgba(6, 13, 26, 0.85)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "16px",
              padding: "24px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#cbd5e1" }}>
                {cleanedView === "clean" ? "✨ Syntropy Clean Normalization" : "⚠️ Raw Cryptic Bank Statement"}
              </div>
              <button
                onClick={() => handleCopySnippet(cleanedView === "clean" ? "Swiggy • Food & Dining • ₹840.00" : "UPI/DR/4291039401/SWIGGY_BLR/HDFC000001")}
                style={{
                  background: "none",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#94a3b8",
                  padding: "4px 8px",
                  borderRadius: "6px",
                  fontSize: "0.72rem",
                  cursor: "pointer",
                }}
              >
                Copy Line
              </button>
            </div>

            {/* Line Demo */}
            {cleanedView === "clean" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ padding: "12px", background: "rgba(16,185,129,0.08)", borderRadius: "8px", border: "1px solid rgba(16,185,129,0.2)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
                    <span>🍔 Swiggy Gourmet</span>
                    <span>-₹840.00</span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#34d399", marginTop: "4px" }}>
                    Verified Merchant: Swiggy India • Category: Food & Dining • Mode: UPI
                  </div>
                </div>

                <div style={{ padding: "12px", background: "rgba(16,185,129,0.08)", borderRadius: "8px", border: "1px solid rgba(16,185,129,0.2)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
                    <span>🎬 Netflix India</span>
                    <span>-₹649.00</span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#34d399", marginTop: "4px" }}>
                    Recurring Autopay: Active • Next deduction: Oct 04, 2026
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ padding: "12px", background: "rgba(239,68,68,0.08)", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.2)", fontFamily: "monospace", fontSize: "0.78rem", color: "#fca5a5" }}>
                  4291039401/UPI/DR/SWIGGY_BLR/HDFC000001/NA/PAY_01920391024/0907
                </div>
                <div style={{ padding: "12px", background: "rgba(239,68,68,0.08)", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.2)", fontFamily: "monospace", fontSize: "0.78rem", color: "#fca5a5" }}>
                  ACH/DR/NFLX_NETFLIX_MUMBAI/E-MANDATE_00291023910/AUTODBT_SEP04
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
              <button
                onClick={() => handleCopySnippet("Syntropy Export: 284 Clean Transactions - September 2026.csv")}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#cbd5e1",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                📥 Export Clean CSV
              </button>
              <button
                onClick={() => handleCopySnippet("Tax-Ready ITR Statement 2026-27.pdf")}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#cbd5e1",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                📄 Tax-Ready PDF
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Feature 3: AI Financial Co-pilot Simulation ────────────────────── */}
      <section
        id="ai"
        style={{
          maxWidth: "1280px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "700px", margin: "0 auto 40px" }}>
          <span style={{ color: "#8b5cf6", fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            AUTONOMOUS INSIGHTS
          </span>
          <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 800, margin: "12px 0", letterSpacing: "-0.03em" }}>
            Ask questions. Don&apos;t drown in charts.
          </h2>
          <p style={{ color: "#94a3b8", fontSize: "1.05rem" }}>
            Click any question below to see how Syntropy&apos;s financial engine parses cross-bank data in milliseconds:
          </p>
        </div>

        {/* Clickable Prompts */}
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "10px", marginBottom: "28px" }}>
          {aiPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => {
                setActivePromptIndex(idx);
                Analytics.demoInteracted("ai_prompt_clicked", { prompt: p.q });
              }}
              style={{
                background: activePromptIndex === idx ? "linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%)" : "rgba(255, 255, 255, 0.04)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                color: activePromptIndex === idx ? "#fff" : "#94a3b8",
                fontWeight: 600,
                fontSize: "0.85rem",
                padding: "8px 16px",
                borderRadius: "99px",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              {p.q}
            </button>
          ))}
        </div>

        {/* Selected AI Response Card */}
        <div
          style={{
            maxWidth: "780px",
            margin: "0 auto",
            background: "linear-gradient(180deg, rgba(13, 24, 41, 0.8) 0%, rgba(6, 13, 26, 0.9) 100%)",
            border: "1px solid rgba(139, 92, 246, 0.3)",
            borderRadius: "20px",
            padding: "32px",
            boxShadow: "0 10px 40px rgba(139, 92, 246, 0.1)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <span style={{ fontSize: "0.8rem", color: "#a78bfa", fontWeight: 700, textTransform: "uppercase" }}>
              ✦ {aiPrompts[activePromptIndex].tag}
            </span>
            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Calculated across HDFC, ICICI, SBI</span>
          </div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#f8fafc", marginBottom: "12px" }}>
            &ldquo;{aiPrompts[activePromptIndex].q}&rdquo;
          </div>
          <div style={{ fontSize: "1rem", color: "#cbd5e1", lineHeight: 1.6 }}>
            {aiPrompts[activePromptIndex].a}
          </div>
        </div>
      </section>

      {/* ── Feature 4: Supported Banks Radar ──────────────────────────────── */}
      <section
        id="banks"
        style={{
          maxWidth: "1280px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "700px", margin: "0 auto 40px" }}>
          <span style={{ color: "#10b981", fontSize: "0.82rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            NETWORK COVERAGE
          </span>
          <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 800, margin: "12px 0", letterSpacing: "-0.03em" }}>
            Connected to 40+ Indian financial institutions.
          </h2>
          <p style={{ color: "#94a3b8", fontSize: "1.05rem" }}>
            All major public and private sector banks in India are live on the Account Aggregator network.
          </p>
        </div>

        {/* Bank Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
            gap: "16px",
          }}
        >
          {SUPPORTED_BANKS.map((b, i) => (
            <div
              key={i}
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                borderRadius: "14px",
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "#f8fafc" }}>{b.name}</div>
                <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>AA Protocol v2.0</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    fontSize: "0.72rem",
                    color: "#34d399",
                    fontWeight: 700,
                  }}
                >
                  <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981" }} />
                  {b.uptime}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── VIP Early Access Banner ───────────────────────────────────────── */}
      <section
        style={{
          maxWidth: "1280px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            background: "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 182, 212, 0.1) 100%)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "24px",
            padding: "60px 32px",
            textAlign: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 900, letterSpacing: "-0.03em", marginBottom: "16px" }}>
            Ready to take back control of your financial life?
          </h2>
          <p style={{ color: "#cbd5e1", fontSize: "1.1rem", maxWidth: "600px", margin: "0 auto 32px", lineHeight: 1.6 }}>
            Join smart Indian engineers, founders, and creators managing their money with clarity. Zero password sharing. Zero spam.
          </p>

          <div style={{ display: "flex", justifyContent: "center", gap: "12px", flexWrap: "wrap" }}>
            <button
              onClick={handleLaunchFullDemo}
              style={{
                background: "#10b981",
                border: "none",
                color: "#060d1a",
                fontWeight: 800,
                fontSize: "1rem",
                padding: "14px 28px",
                borderRadius: "12px",
                cursor: "pointer",
                boxShadow: "0 0 30px rgba(16, 185, 129, 0.4)",
              }}
            >
              Launch Live App ⚡
            </button>
            <button
              onClick={() => navigate("/login")}
              style={{
                background: "rgba(255, 255, 255, 0.08)",
                border: "1px solid rgba(255, 255, 255, 0.2)",
                color: "#fff",
                fontWeight: 600,
                fontSize: "1rem",
                padding: "14px 26px",
                borderRadius: "12px",
                cursor: "pointer",
              }}
            >
              Sign In or Register ↗
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer
        style={{
          borderTop: "1px solid rgba(255, 255, 255, 0.06)",
          padding: "60px 24px 40px",
          background: "rgba(6, 13, 26, 0.95)",
        }}
      >
        <div
          style={{
            maxWidth: "1280px",
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "40px",
            marginBottom: "50px",
          }}
        >
          <div>
            <div className="logo-mark grad-text" style={{ fontSize: "1.4rem", fontWeight: 800, marginBottom: "12px" }}>
              ✦ Syntropy
            </div>
            <p style={{ color: "#64748b", fontSize: "0.85rem", lineHeight: 1.6 }}>
              Open Finance personal intelligence platform for India. Built on the Reserve Bank of India (RBI) Account Aggregator architecture.
            </p>
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "#f8fafc", marginBottom: "14px" }}>Product</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem", color: "#94a3b8" }}>
              <a href="#simulator" style={{ color: "#94a3b8", textDecoration: "none" }}>Live Simulator</a>
              <a href="#cleaner" style={{ color: "#94a3b8", textDecoration: "none" }}>Statement Cleaner</a>
              <a href="#privacy" style={{ color: "#94a3b8", textDecoration: "none" }}>Privacy Comparison</a>
              <a href="#banks" style={{ color: "#94a3b8", textDecoration: "none" }}>Supported Banks</a>
            </div>
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "#f8fafc", marginBottom: "14px" }}>Integration</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem", color: "#94a3b8" }}>
              <a href="https://bridge.setu.co" target="_blank" rel="noreferrer" style={{ color: "#94a3b8", textDecoration: "none" }}>Setu Bridge AA</a>
              <a href="https://sahamati.org.in" target="_blank" rel="noreferrer" style={{ color: "#94a3b8", textDecoration: "none" }}>Sahamati Alliance</a>
              <a href="https://api.rebit.org.in" target="_blank" rel="noreferrer" style={{ color: "#94a3b8", textDecoration: "none" }}>ReBIT AA Schemas</a>
            </div>
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "#f8fafc", marginBottom: "14px" }}>Security & Legal</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem", color: "#94a3b8" }}>
              <span style={{ color: "#64748b" }}>256-bit TLS Encryption</span>
              <span style={{ color: "#64748b" }}>RBI Master Directions (NBFC-AA)</span>
              <span style={{ color: "#64748b" }}>Zero Data Selling Guarantee</span>
            </div>
          </div>
        </div>

        <div
          style={{
            maxWidth: "1280px",
            margin: "0 auto",
            paddingTop: "24px",
            borderTop: "1px solid rgba(255, 255, 255, 0.04)",
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "16px",
            color: "#64748b",
            fontSize: "0.8rem",
          }}
        >
          <div>
            © {new Date().getFullYear()} Syntropy Technologies. All rights reserved.
          </div>
          <div>
            Syntropy acts as a Technology Service Provider (TSP) integrating through licensed RBI Account Aggregators.
          </div>
        </div>
      </footer>
    </div>
  );
}
