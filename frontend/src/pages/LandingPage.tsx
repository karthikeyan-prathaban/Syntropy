import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { demoLogin, getWaitlistCount, joinWaitlist, loadMockData } from "../api/client";
import { Analytics, getStoredUTMs } from "../utils/analytics";

// ── Types & Mock Data ────────────────────────────────────────────────────────

interface BankCardData {
  id: string;
  name: string;
  shortName: string;
  accNumber: string;
  balance: number;
  type: string;
  color: string;
  textColor: string;
  chipColor: string;
  tag: string;
}

interface SearchPreset {
  id: string;
  label: string;
  query: string;
  icon: string;
  amount: number;
  type: "DEBIT" | "CREDIT" | "EMPTY";
  count: number;
  category: string;
  bank: string;
  date: string;
  commentary: string;
  rawLine: string;
}

const BANK_CARDS: BankCardData[] = [
  {
    id: "hdfc",
    name: "HDFC Bank",
    shortName: "HDFC",
    accNumber: "•••• 4920",
    balance: 342850,
    type: "Salary & Daily Spends",
    color: "linear-gradient(135deg, #0A2D67 0%, #1E3A8A 100%)",
    textColor: "#FFFFFF",
    chipColor: "#FDE047",
    tag: "Primary Salary",
  },
  {
    id: "icici",
    name: "ICICI Bank",
    shortName: "ICICI",
    accNumber: "•••• 8104",
    balance: 194500,
    type: "Consulting & Current A/C",
    color: "linear-gradient(135deg, #7C2D12 0%, #C2410C 100%)",
    textColor: "#FFFFFF",
    chipColor: "#E2E8F0",
    tag: "Business / Inward",
  },
  {
    id: "sbi",
    name: "State Bank of India",
    shortName: "SBI",
    accNumber: "•••• 2291",
    balance: 88200,
    type: "Emergency Reserve",
    color: "linear-gradient(135deg, #064E3B 0%, #047857 100%)",
    textColor: "#FFFFFF",
    chipColor: "#FDE047",
    tag: "High-Yield FD",
  },
  {
    id: "zerodha",
    name: "Zerodha & Groww",
    shortName: "Investments",
    accNumber: "•••• 7712",
    balance: 814000,
    type: "Mutual Funds & Equities",
    color: "linear-gradient(135deg, #18181B 0%, #27272A 100%)",
    textColor: "#FFFFFF",
    chipColor: "#67E8F9",
    tag: "Portfolio",
  },
];

const SEARCH_PRESETS: SearchPreset[] = [
  {
    id: "mcdonalds",
    label: "McDonald's",
    query: "McDonald's",
    icon: "🍔",
    amount: 4850,
    type: "DEBIT",
    count: 14,
    category: "Food & Dining",
    bank: "HDFC •••• 4920",
    date: "14 visits in last 90 days",
    commentary: "You spent ₹4,850 on late-night burgers this quarter. Look yourself in the mirror, stop ordering at 2 AM.",
    rawLine: "4291039401/UPI/DR/MCDONALDS_IN/HDFC000001/029103",
  },
  {
    id: "coffee",
    label: "Blue Tokai Coffee",
    query: "Blue Tokai",
    icon: "☕",
    amount: 4180,
    type: "DEBIT",
    count: 19,
    category: "Food & Dining",
    bank: "HDFC •••• 4920",
    date: "19 visits in last 90 days",
    commentary: "Your daily caffeine tax. At ₹220 per iced pour-over, this amounts to ₹16,720 annually.",
    rawLine: "UPI/DR/4290119283/BLUETOKAI_ROASTERS/YESB000001",
  },
  {
    id: "gym",
    label: "Cult.fit Gym",
    query: "Cult.fit",
    icon: "🏋️",
    amount: 0,
    type: "EMPTY",
    count: 0,
    category: "Fitness & Wellness",
    bank: "None",
    date: "0 visits found",
    commentary: "Realize there's zero transactions found. We won't judge your fitness streak, but your bank account noticed.",
    rawLine: "NO_TRANSACTIONS_FOUND_IN_SELECTED_PERIOD",
  },
  {
    id: "salary",
    label: "Consulting Payout",
    query: "Stripe Payout",
    icon: "💼",
    amount: 125000,
    type: "CREDIT",
    count: 1,
    category: "Income",
    bank: "ICICI •••• 8104",
    date: "Today, 10:30 AM",
    commentary: "Foreign inward remittance cleared cleanly. Auto-tagged under Professional Consulting Income for advance tax.",
    rawLine: "NEFT/CR/STRPIND092301/STRIPE_CONSULTING_PAYOUT",
  },
  {
    id: "sip",
    label: "Nifty 50 Index SIP",
    query: "Index SIP",
    icon: "📈",
    amount: 25000,
    type: "DEBIT",
    count: 3,
    category: "Investments",
    bank: "Zerodha •••• 7712",
    date: "Sep 05, 9:00 AM",
    commentary: "Disciplined auto-investing at work. Your portfolio compound rate is tracking at 14.8% XIRR.",
    rawLine: "ACH/DR/ZRDHMF002910/AUTOPAY_NIFTY50_DIRECT_GROWTH",
  },
];

const SUPPORTED_BANKS = [
  { name: "HDFC Bank", uptime: "99.9%", code: "HDFC", icon: "🏛️" },
  { name: "State Bank of India", uptime: "99.5%", code: "SBIN", icon: "🇮🇳" },
  { name: "ICICI Bank", uptime: "99.8%", code: "ICIC", icon: "🏦" },
  { name: "Axis Bank", uptime: "99.7%", code: "UTIB", icon: "🏛️" },
  { name: "Kotak Mahindra", uptime: "99.9%", code: "KKBK", icon: "🏦" },
  { name: "IndusInd Bank", uptime: "99.6%", code: "INDB", icon: "🏛️" },
  { name: "Federal Bank", uptime: "99.9%", code: "FDRL", icon: "🏦" },
  { name: "IDFC FIRST Bank", uptime: "99.9%", code: "IDFB", icon: "🏛️" },
  { name: "Punjab National Bank", uptime: "99.2%", code: "PUNB", icon: "🇮🇳" },
  { name: "Bank of Baroda", uptime: "99.4%", code: "BARB", icon: "🏛️" },
  { name: "Zerodha Broking", uptime: "99.9%", code: "ZRDH", icon: "📈" },
  { name: "Groww (Nextbillion)", uptime: "99.8%", code: "GROW", icon: "📊" },
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
  const [email, setEmail] = useState("");
  const [waitlistLoading, setWaitlistLoading] = useState(false);
  const [waitlistRank, setWaitlistRank] = useState<number | null>(null);
  const [waitlistError, setWaitlistError] = useState("");
  const [waitlistCount, setWaitlistCount] = useState(14820);

  // Search & Recall Interactive feature
  const [activePreset, setActivePreset] = useState<SearchPreset>(SEARCH_PRESETS[0]);
  const [manualQuery, setManualQuery] = useState("");

  // Bank Card Interactive feature
  const [selectedCardId, setSelectedCardId] = useState("hdfc");

  // Statement cleaner toggle
  const [cleanerMode, setCleanerMode] = useState<"clean" | "raw">("clean");
  const [toastMessage, setToastMessage] = useState("");

  useEffect(() => {
    Analytics.pageView("Landing Page (Light Theme)");
    getWaitlistCount()
      .then((res) => {
        if (res?.count) setWaitlistCount(14800 + res.count);
      })
      .catch(() => {});
  }, []);

  const totalNetWorth = useMemo(() => {
    return BANK_CARDS.reduce((sum, b) => sum + b.balance, 0);
  }, []);

  const activeCard = useMemo(() => {
    return BANK_CARDS.find((c) => c.id === selectedCardId) || BANK_CARDS[0];
  }, [selectedCardId]);

  async function handleWaitlist(e: FormEvent) {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      setWaitlistError("Please provide a valid email.");
      return;
    }
    setWaitlistLoading(true);
    setWaitlistError("");
    try {
      const utms = getStoredUTMs();
      const res = await joinWaitlist({
        email,
        source: "light_landing",
        utm: utms as any,
      });
      const pos = res.position || waitlistCount + 1;
      setWaitlistRank(pos);
      setWaitlistCount((c) => c + 1);
      Analytics.waitlistJoined(email, pos);
    } catch (err: any) {
      setWaitlistError(err?.message || "Error joining waitlist.");
    } finally {
      setWaitlistLoading(false);
    }
  }

  async function launchDemoApp() {
    Analytics.demoInteracted("hero_launch_demo");
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
    }
  }

  function showToast(msg: string) {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(""), 2200);
  }

  return (
    <div style={{ background: "#FAF9F6", color: "#0F172A", minHeight: "100vh", position: "relative" }}>
      {/* ── Toast Notification ────────────────────────────────────────────── */}
      {toastMessage && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 9999,
            background: "#0F172A",
            color: "#FFFFFF",
            padding: "10px 18px",
            borderRadius: "10px",
            fontSize: "0.85rem",
            fontWeight: 600,
            boxShadow: "0 10px 30px rgba(0,0,0,0.15)",
          }}
        >
          ✓ {toastMessage}
        </div>
      )}

      {/* ── Top Navigation Bar ────────────────────────────────────────────── */}
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 100,
          background: "rgba(250, 249, 246, 0.88)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(15, 23, 42, 0.06)",
          padding: "16px 24px",
        }}
      >
        <div
          style={{
            maxWidth: "1280px",
            margin: "0 auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Logo & Regulatory Pill */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "1.45rem", fontWeight: 900, color: "#0F172A", fontFamily: "'Space Grotesk', sans-serif" }}>
                ✦ syntropy
              </span>
            </Link>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "0.72rem",
                padding: "3px 10px",
                borderRadius: "99px",
                background: "#ECFDF5",
                color: "#065F46",
                border: "1px solid #A7F3D0",
                fontWeight: 700,
              }}
            >
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#059669" }} />
              RBI AA Gateway Active
            </span>
          </div>

          {/* Desktop Nav Links */}
          <div style={{ display: "none", alignItems: "center", gap: "24px" }} className="desktop-links">
            <a href="#search-recall" style={{ color: "#475569", textDecoration: "none", fontSize: "0.88rem", fontWeight: 600 }}>
              Search &amp; Recall
            </a>
            <a href="#bank-stack" style={{ color: "#475569", textDecoration: "none", fontSize: "0.88rem", fontWeight: 600 }}>
              Multi-Bank Stack
            </a>
            <a href="#cleaner" style={{ color: "#475569", textDecoration: "none", fontSize: "0.88rem", fontWeight: 600 }}>
              Clean Statements
            </a>
            <a href="#architecture" style={{ color: "#475569", textDecoration: "none", fontSize: "0.88rem", fontWeight: 600 }}>
              No SMS Scraping
            </a>
            <a href="#banks" style={{ color: "#475569", textDecoration: "none", fontSize: "0.88rem", fontWeight: 600 }}>
              40+ Banks
            </a>
          </div>

          {/* Action CTAs */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              onClick={() => {
                Analytics.ctaClicked("sign_in_nav", "nav");
                navigate("/login");
              }}
              style={{
                background: "transparent",
                border: "1px solid #E2E4E9",
                color: "#0F172A",
                padding: "8px 16px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
              }}
            >
              Sign In
            </button>
            <button
              onClick={launchDemoApp}
              style={{
                background: "#0F172A",
                border: "none",
                color: "#FFFFFF",
                padding: "8px 18px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 700,
                cursor: "pointer",
                boxShadow: "0 2px 8px rgba(15, 23, 42, 0.18)",
              }}
            >
              Launch App ⚡
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero Section with Animated Blueprint Grid ─────────────────────── */}
      <header
        style={{
          position: "relative",
          padding: "64px 24px 60px",
          maxWidth: "1280px",
          margin: "0 auto",
          textAlign: "center",
          overflow: "hidden",
        }}
      >
        {/* Animated Blueprint Grid Graphic (Fold-inspired architectural SVG) */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: "50%",
            transform: "translateX(-50%)",
            width: "1200px",
            height: "400px",
            pointerEvents: "none",
            opacity: 0.45,
            zIndex: 0,
          }}
        >
          <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="blueprint-grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#E2E4E9" strokeWidth="1" className="animate-dash-blueprint" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#blueprint-grid)" />
          </svg>
        </div>

        <div style={{ position: "relative", zIndex: 1, maxWidth: "920px", margin: "0 auto" }}>
          {/* Tactile Playful Pill (Fold aesthetic) */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 14px",
              borderRadius: "99px",
              background: "#FFFFFF",
              border: "1px solid #E2E4E9",
              boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
              fontSize: "0.82rem",
              fontWeight: 600,
              color: "#334155",
              marginBottom: "24px",
            }}
          >
            <span style={{ fontSize: "1rem" }}>😜</span>
            <span>Be painfully aware.</span>
            <span style={{ color: "#94A3B8" }}>•</span>
            <span style={{ color: "#059669", fontWeight: 700 }}>Zero SMS Scraping</span>
          </div>

          {/* Editorial Display Heading */}
          <h1
            style={{
              fontSize: "clamp(2.5rem, 6.2vw, 4.6rem)",
              fontWeight: 900,
              letterSpacing: "-0.04em",
              lineHeight: 1.05,
              color: "#0F172A",
              marginBottom: "22px",
            }}
          >
            See every rupee.<br />
            <span style={{ color: "#2563EB" }}>With surgical clarity.</span>
          </h1>

          {/* Subtitle */}
          <p
            style={{
              fontSize: "clamp(1.05rem, 2.2vw, 1.25rem)",
              color: "#475569",
              maxWidth: "720px",
              margin: "0 auto 36px",
              lineHeight: 1.6,
              fontWeight: 450,
            }}
          >
            Syntropy connects all your bank accounts through the Government-regulated Account Aggregator Framework.
            Never let shady apps read your personal SMS or Gmail again.
          </p>

          {/* Hero CTAs */}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "12px", marginBottom: "32px" }}>
            <button
              onClick={launchDemoApp}
              style={{
                background: "#0F172A",
                color: "#FFFFFF",
                fontWeight: 700,
                fontSize: "1rem",
                padding: "14px 28px",
                borderRadius: "12px",
                border: "none",
                cursor: "pointer",
                boxShadow: "0 4px 14px rgba(15, 23, 42, 0.25)",
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                transition: "transform 0.15s ease",
              }}
            >
              <span>Explore Live Terminal</span>
              <span>⚡</span>
            </button>

            <button
              onClick={() => {
                Analytics.ctaClicked("connect_bank_hero", "hero");
                navigate("/login");
              }}
              style={{
                background: "#FFFFFF",
                color: "#0F172A",
                fontWeight: 700,
                fontSize: "1rem",
                padding: "14px 26px",
                borderRadius: "12px",
                border: "1px solid #E2E4E9",
                cursor: "pointer",
                boxShadow: "0 2px 4px rgba(0,0,0,0.04)",
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span>Connect Bank (Setu AA)</span>
              <span>🏦</span>
            </button>
          </div>

          {/* Tactile Waitlist Form */}
          <form
            onSubmit={handleWaitlist}
            style={{
              maxWidth: "460px",
              margin: "0 auto 24px",
              display: "flex",
              gap: "8px",
              background: "#FFFFFF",
              padding: "6px",
              borderRadius: "14px",
              border: "1px solid #E2E4E9",
              boxShadow: "0 4px 16px rgba(0,0,0,0.04)",
            }}
          >
            <input
              type="email"
              placeholder="Enter email for VIP early access..."
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                padding: "10px 16px",
                fontSize: "0.92rem",
                color: "#0F172A",
                background: "transparent",
              }}
            />
            <button
              type="submit"
              disabled={waitlistLoading}
              style={{
                background: "#2563EB",
                color: "#FFFFFF",
                border: "none",
                padding: "10px 20px",
                borderRadius: "10px",
                fontWeight: 700,
                fontSize: "0.88rem",
                cursor: "pointer",
                whiteSpace: "nowrap",
                boxShadow: "0 2px 8px rgba(37, 99, 235, 0.25)",
              }}
            >
              {waitlistLoading ? "Reserving..." : "Get Access"}
            </button>
          </form>

          {waitlistRank && (
            <div
              style={{
                display: "inline-block",
                padding: "8px 16px",
                borderRadius: "10px",
                background: "#ECFDF5",
                color: "#065F46",
                fontWeight: 700,
                fontSize: "0.88rem",
                marginBottom: "20px",
                border: "1px solid #A7F3D0",
              }}
            >
              🎉 Reserved spot #{waitlistRank.toLocaleString()}! We&apos;ll notify you on priority.
            </div>
          )}
          {waitlistError && (
            <div style={{ color: "#E11D48", fontSize: "0.85rem", marginBottom: "20px" }}>{waitlistError}</div>
          )}

          {/* Social Proof Pill Bar */}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "16px", color: "#64748B", fontSize: "0.82rem", fontWeight: 500 }}>
            <span>✓ {waitlistCount.toLocaleString()}+ on early waitlist</span>
            <span>•</span>
            <span>✓ 40+ Indian Banks Live</span>
            <span>•</span>
            <span>✓ End-to-End Encrypted Pipes</span>
          </div>
        </div>
      </header>

      {/* ── Feature 1: "Search. Recall. Filter." (Signature Fold Feature Recreated) ── */}
      <section
        id="search-recall"
        style={{
          maxWidth: "1100px",
          margin: "30px auto 100px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E4E9",
            borderRadius: "28px",
            padding: "40px 36px",
            boxShadow: "0 10px 40px -10px rgba(15, 23, 42, 0.05)",
            textAlign: "center",
          }}
        >
          {/* Header */}
          <div style={{ maxWidth: "600px", margin: "0 auto 28px" }}>
            <span style={{ color: "#2563EB", fontWeight: 700, fontSize: "0.82rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              INSTANT TRANSACTION RECALL
            </span>
            <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", fontWeight: 800, margin: "10px 0 12px" }}>
              Search. Recall. Filter.
            </h2>
            <p style={{ color: "#64748B", fontSize: "0.98rem", lineHeight: 1.6 }}>
              Not just rows in a spreadsheet, but the entire story. Click any search preset below or type to search across all your connected bank accounts:
            </p>
          </div>

          {/* Query Preset Pills */}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px", marginBottom: "28px" }}>
            {SEARCH_PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => {
                  setActivePreset(preset);
                  setManualQuery(preset.query);
                  Analytics.searchQueried(preset.query);
                }}
                style={{
                  background: activePreset.id === preset.id ? "#0F172A" : "#F1F5F9",
                  color: activePreset.id === preset.id ? "#FFFFFF" : "#334155",
                  border: `1px solid ${activePreset.id === preset.id ? "#0F172A" : "#E2E8F0"}`,
                  padding: "8px 16px",
                  borderRadius: "99px",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  transition: "all 0.15s ease",
                }}
              >
                <span>{preset.icon}</span>
                <span>{preset.label}</span>
              </button>
            ))}
          </div>

          {/* Live Search Terminal Box (Fold-style dark/high-contrast viewport inside light canvas) */}
          <div
            style={{
              maxWidth: "680px",
              margin: "0 auto",
              background: "#1E293B",
              borderRadius: "20px",
              padding: "24px 28px",
              color: "#FFFFFF",
              boxShadow: "0 20px 50px rgba(15, 23, 42, 0.2)",
              textAlign: "left",
            }}
          >
            {/* Search Input Bar */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingBottom: "16px",
                borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                marginBottom: "20px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1 }}>
                <span style={{ fontSize: "1.2rem", opacity: 0.6 }}>🔍</span>
                <span style={{ fontSize: "1.35rem", fontWeight: 700, color: "#F8FAFC" }}>
                  {manualQuery || activePreset.query}
                </span>
                <span style={{ width: "2px", height: "24px", background: "#38BDF8", display: "inline-block", animation: "pulseGlow 1s infinite" }} />
              </div>
              <span
                style={{
                  background: "rgba(255, 255, 255, 0.1)",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  color: "#94A3B8",
                }}
              >
                {activePreset.count} Matches
              </span>
            </div>

            {/* Displayed Transaction Card */}
            {activePreset.type === "EMPTY" ? (
              <div
                style={{
                  background: "rgba(255, 255, 255, 0.04)",
                  borderRadius: "14px",
                  padding: "24px",
                  textAlign: "center",
                  border: "1px dashed rgba(255, 255, 255, 0.15)",
                }}
              >
                <div style={{ fontSize: "2rem", marginBottom: "8px" }}>🧘</div>
                <div style={{ fontWeight: 700, fontSize: "1.05rem", color: "#F8FAFC" }}>
                  No transactions recorded
                </div>
                <div style={{ fontSize: "0.85rem", color: "#94A3B8", marginTop: "4px" }}>
                  {activePreset.commentary}
                </div>
              </div>
            ) : (
              <div
                style={{
                  background: "rgba(255, 255, 255, 0.05)",
                  borderRadius: "14px",
                  padding: "20px",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "1.3rem" }}>{activePreset.icon}</span>
                    <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "#FFFFFF" }}>{activePreset.label}</span>
                  </div>
                  <div
                    style={{
                      fontSize: "1.8rem",
                      fontWeight: 900,
                      color: activePreset.type === "CREDIT" ? "#34D399" : "#F8FAFC",
                    }}
                  >
                    {activePreset.type === "CREDIT" ? "+" : "-"}{fmtINR(activePreset.amount)}
                  </div>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", fontSize: "0.78rem", color: "#94A3B8", marginBottom: "14px" }}>
                  <span>{activePreset.date}</span>
                  <span>•</span>
                  <span style={{ color: "#38BDF8" }}>{activePreset.category}</span>
                  <span>•</span>
                  <span>{activePreset.bank}</span>
                </div>

                {/* Humorous / Insightful Commentary */}
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "8px",
                    background: "rgba(37, 99, 235, 0.15)",
                    border: "1px solid rgba(37, 99, 235, 0.3)",
                    color: "#93C5FD",
                    fontSize: "0.85rem",
                    lineHeight: 1.5,
                  }}
                >
                  💡 <strong>Syntropy Insight:</strong> {activePreset.commentary}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Feature 2: Interactive 3D Multi-Bank Stack ────────────────────── */}
      <section
        id="bank-stack"
        style={{
          maxWidth: "1280px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "680px", margin: "0 auto 40px" }}>
          <span style={{ color: "#059669", fontWeight: 700, fontSize: "0.82rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            CROSS-BANK UNIFICATION
          </span>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", fontWeight: 800, margin: "10px 0 12px" }}>
            All your bank accounts. In one tactile stack.
          </h2>
          <p style={{ color: "#64748B", fontSize: "1rem", lineHeight: 1.6 }}>
            Click any bank card below to switch accounts and inspect live balances:
          </p>
        </div>

        {/* 4 Cards Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "20px",
            marginBottom: "36px",
          }}
        >
          {BANK_CARDS.map((card) => {
            const isSelected = card.id === selectedCardId;
            return (
              <div
                key={card.id}
                onClick={() => {
                  setSelectedCardId(card.id);
                  Analytics.bankSwitched(card.name);
                }}
                style={{
                  background: card.color,
                  borderRadius: "20px",
                  padding: "24px",
                  color: card.textColor,
                  cursor: "pointer",
                  position: "relative",
                  overflow: "hidden",
                  boxShadow: isSelected
                    ? "0 20px 40px -10px rgba(15, 23, 42, 0.35), 0 0 0 3px #2563EB"
                    : "0 6px 20px rgba(0,0,0,0.06)",
                  transform: isSelected ? "translateY(-6px) scale(1.02)" : "translateY(0px)",
                  transition: "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px" }}>
                  <div>
                    <div style={{ fontSize: "1.1rem", fontWeight: 800 }}>{card.name}</div>
                    <div style={{ fontSize: "0.78rem", opacity: 0.75, marginTop: "2px" }}>{card.type}</div>
                  </div>
                  {/* EMV Chip Graphic */}
                  <div
                    style={{
                      width: "36px",
                      height: "26px",
                      borderRadius: "6px",
                      background: card.chipColor,
                      border: "1px solid rgba(0,0,0,0.1)",
                      opacity: 0.85,
                    }}
                  />
                </div>

                <div style={{ fontSize: "1.9rem", fontWeight: 900, letterSpacing: "-0.03em", marginBottom: "8px" }}>
                  {fmtINR(card.balance)}
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem", opacity: 0.85 }}>
                  <span style={{ fontFamily: "monospace", letterSpacing: "0.1em" }}>{card.accNumber}</span>
                  <span
                    style={{
                      background: "rgba(255,255,255,0.2)",
                      padding: "2px 8px",
                      borderRadius: "6px",
                      fontSize: "0.72rem",
                      fontWeight: 600,
                    }}
                  >
                    {card.tag}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Aggregated Total Banner */}
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E4E9",
            borderRadius: "18px",
            padding: "20px 28px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.03)",
          }}
        >
          <div>
            <div style={{ fontSize: "0.78rem", color: "#64748B", fontWeight: 700, textTransform: "uppercase" }}>
              Total Aggregated Net Worth
            </div>
            <div style={{ fontSize: "2rem", fontWeight: 900, color: "#0F172A" }}>
              {fmtINR(totalNetWorth)}
            </div>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={() => showToast("Account statement export generated!")}
              style={{
                background: "#F1F5F9",
                border: "1px solid #E2E8F0",
                color: "#0F172A",
                padding: "10px 18px",
                borderRadius: "10px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              📥 Download Combined Statement
            </button>
            <button
              onClick={launchDemoApp}
              style={{
                background: "#0F172A",
                border: "none",
                color: "#FFFFFF",
                padding: "10px 20px",
                borderRadius: "10px",
                fontSize: "0.85rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              View Full Analytics →
            </button>
          </div>
        </div>
      </section>

      {/* ── Feature 3: Bank Statement Cleaner (Fold-Style Tactile UI) ─────── */}
      <section
        id="cleaner"
        style={{
          maxWidth: "1100px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E4E9",
            borderRadius: "28px",
            padding: "48px 36px",
            boxShadow: "0 6px 30px rgba(0,0,0,0.04)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "40px",
            alignItems: "center",
          }}
        >
          {/* Left Text */}
          <div>
            <span style={{ color: "#2563EB", fontWeight: 700, fontSize: "0.82rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              NEVER VISIT NETBANKING AGAIN
            </span>
            <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", fontWeight: 800, margin: "10px 0 14px", lineHeight: 1.2 }}>
              Clean, password-free statements. Without the headache.
            </h2>
            <p style={{ color: "#475569", fontSize: "1rem", lineHeight: 1.6, marginBottom: "24px" }}>
              Banks give you cryptic strings like <code>UPI/CR/429019284102/PYTM...</code> that break in Excel. Syntropy normalizes them into clean merchant names with 1-click tax CSV &amp; PDF exports.
            </p>

            <div style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={() => setCleanerMode("clean")}
                style={{
                  background: cleanerMode === "clean" ? "#0F172A" : "#F1F5F9",
                  color: cleanerMode === "clean" ? "#FFFFFF" : "#334155",
                  border: "none",
                  padding: "9px 18px",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                }}
              >
                Syntropy Clean View
              </button>
              <button
                onClick={() => setCleanerMode("raw")}
                style={{
                  background: cleanerMode === "raw" ? "#E11D48" : "#F1F5F9",
                  color: cleanerMode === "raw" ? "#FFFFFF" : "#334155",
                  border: "none",
                  padding: "9px 18px",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                }}
              >
                Raw Bank PDF View
              </button>
            </div>
          </div>

          {/* Right Comparison Display */}
          <div
            style={{
              background: "#FAF9F6",
              border: "1px solid #E2E4E9",
              borderRadius: "20px",
              padding: "24px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "#0F172A" }}>
                {cleanerMode === "clean" ? "✨ Syntropy Clean Normalization" : "⚠️ Raw Ugly Bank SMS/PDF"}
              </span>
              <button
                onClick={() => showToast("Copied statement line to clipboard!")}
                style={{
                  background: "#FFFFFF",
                  border: "1px solid #E2E4E9",
                  color: "#475569",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Copy Line
              </button>
            </div>

            {cleanerMode === "clean" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ padding: "14px", background: "#FFFFFF", borderRadius: "10px", border: "1px solid #E2E4E9" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
                    <span>🍔 Swiggy Gourmet</span>
                    <span style={{ color: "#E11D48" }}>-₹840.00</span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#059669", marginTop: "4px", fontWeight: 600 }}>
                    Verified Merchant: Swiggy • Food &amp; Dining • Mode: UPI
                  </div>
                </div>

                <div style={{ padding: "14px", background: "#FFFFFF", borderRadius: "10px", border: "1px solid #E2E4E9" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
                    <span>🎬 Netflix Premium 4K</span>
                    <span style={{ color: "#E11D48" }}>-₹649.00</span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#059669", marginTop: "4px", fontWeight: 600 }}>
                    Autopay Mandate Active • Next: Oct 04, 2026
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ padding: "14px", background: "#FFF1F2", borderRadius: "10px", border: "1px solid #FECDD3", fontFamily: "monospace", fontSize: "0.78rem", color: "#9F1239" }}>
                  4291039401/UPI/DR/SWIGGY_BLR/HDFC000001/NA/PAY_01920391024/0907
                </div>
                <div style={{ padding: "14px", background: "#FFF1F2", borderRadius: "10px", border: "1px solid #FECDD3", fontFamily: "monospace", fontSize: "0.78rem", color: "#9F1239" }}>
                  ACH/DR/NFLX_NETFLIX_MUMBAI/E-MANDATE_00291023910/AUTODBT_SEP04
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
              <button
                onClick={() => showToast("Exporting Tax Statement 2026.csv...")}
                style={{
                  flex: 1,
                  background: "#0F172A",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "10px",
                  borderRadius: "8px",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                📥 Export Clean CSV
              </button>
              <button
                onClick={() => showToast("Generating Audit-Ready PDF...")}
                style={{
                  flex: 1,
                  background: "#FFFFFF",
                  color: "#0F172A",
                  border: "1px solid #E2E4E9",
                  padding: "10px",
                  borderRadius: "8px",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                📄 Tax-Ready PDF
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Feature 4: Privacy Architecture (The Old Way vs Syntropy) ──────── */}
      <section
        id="architecture"
        style={{
          maxWidth: "1100px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "680px", margin: "0 auto 40px" }}>
          <span style={{ color: "#E11D48", fontWeight: 700, fontSize: "0.82rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            PRIVACY BY DESIGN
          </span>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", fontWeight: 800, margin: "10px 0 12px" }}>
            Stop letting apps read your private SMS and Gmail.
          </h2>
          <p style={{ color: "#64748B", fontSize: "1rem", lineHeight: 1.6 }}>
            Legacy expense trackers ask for dangerous phone permissions to parse bank SMS. Syntropy uses the official RBI Account Aggregator protocol.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }}>
          {/* Old Apps */}
          <div
            style={{
              background: "#FFF1F2",
              border: "1px solid #FECDD3",
              borderRadius: "20px",
              padding: "32px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" }}>
              <span style={{ fontSize: "1.5rem" }}>❌</span>
              <h3 style={{ fontSize: "1.2rem", color: "#9F1239" }}>Old Way (SMS &amp; Email Scraping)</h3>
            </div>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "14px", color: "#881337", fontSize: "0.9rem" }}>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Reads every private OTP and personal SMS message on your device.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Demands Gmail permissions to scrape private email receipts.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Monetizes by selling your profile to loan and credit card telemarketers.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span>✕</span> <span>Impossible to revoke your data once uploaded to their servers.</span>
              </li>
            </ul>
          </div>

          {/* Syntropy Way */}
          <div
            style={{
              background: "#ECFDF5",
              border: "1px solid #A7F3D0",
              borderRadius: "20px",
              padding: "32px",
              boxShadow: "0 6px 24px rgba(5, 150, 105, 0.06)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" }}>
              <span style={{ fontSize: "1.5rem" }}>✅</span>
              <h3 style={{ fontSize: "1.2rem", color: "#065F46" }}>Syntropy (RBI Account Aggregator)</h3>
            </div>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "14px", color: "#064E3B", fontSize: "0.9rem" }}>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ fontWeight: 700 }}>✓</span> <span><strong>Zero SMS access.</strong> Data streams directly from your bank via 256-bit encryption.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ fontWeight: 700 }}>✓</span> <span><strong>Zero email reading.</strong> No Google OAuth or inbox scanning required.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ fontWeight: 700 }}>✓</span> <span><strong>Zero loan telemarketing.</strong> We never sell your data to third parties.</span>
              </li>
              <li style={{ display: "flex", gap: "10px" }}>
                <span style={{ fontWeight: 700 }}>✓</span> <span><strong>One-click revocation</strong> directly through the RBI Account Aggregator registry.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── Feature 5: Supported Banks Radar (Light Theme Cards) ───────────── */}
      <section
        id="banks"
        style={{
          maxWidth: "1100px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "680px", margin: "0 auto 36px" }}>
          <span style={{ color: "#059669", fontWeight: 700, fontSize: "0.82rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            ECOSYSTEM COVERAGE
          </span>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)", fontWeight: 800, margin: "10px 0 12px" }}>
            Live across 40+ Indian Financial Institutions.
          </h2>
          <p style={{ color: "#64748B", fontSize: "1rem" }}>
            Connected directly via Setu FIU to all major public, private, and investment platforms:
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))",
            gap: "14px",
          }}
        >
          {SUPPORTED_BANKS.map((b, i) => (
            <div
              key={i}
              style={{
                background: "#FFFFFF",
                border: "1px solid #E2E4E9",
                borderRadius: "14px",
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "1.2rem" }}>{b.icon}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "#0F172A" }}>{b.name}</div>
                  <div style={{ fontSize: "0.72rem", color: "#94A3B8" }}>{b.code} • Live</div>
                </div>
              </div>
              <span
                style={{
                  fontSize: "0.74rem",
                  fontWeight: 700,
                  color: "#059669",
                  background: "#ECFDF5",
                  padding: "3px 8px",
                  borderRadius: "6px",
                }}
              >
                {b.uptime}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ── VIP Early Access Banner ───────────────────────────────────────── */}
      <section
        style={{
          maxWidth: "1100px",
          margin: "0 auto 100px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            background: "#0F172A",
            color: "#FFFFFF",
            borderRadius: "28px",
            padding: "54px 36px",
            textAlign: "center",
            boxShadow: "0 20px 50px rgba(15, 23, 42, 0.25)",
          }}
        >
          <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 900, marginBottom: "14px", color: "#FFFFFF" }}>
            Ready to lead a healthier financial life?
          </h2>
          <p style={{ color: "#94A3B8", fontSize: "1.05rem", maxWidth: "600px", margin: "0 auto 32px", lineHeight: 1.6 }}>
            Join 14,800+ smart Indian engineers, consultants, and founders managing their money with clarity.
          </p>

          <div style={{ display: "flex", justifyContent: "center", gap: "12px", flexWrap: "wrap" }}>
            <button
              onClick={launchDemoApp}
              style={{
                background: "#2563EB",
                color: "#FFFFFF",
                border: "none",
                fontWeight: 700,
                fontSize: "1rem",
                padding: "14px 28px",
                borderRadius: "12px",
                cursor: "pointer",
                boxShadow: "0 4px 14px rgba(37, 99, 235, 0.4)",
              }}
            >
              Launch Live App ⚡
            </button>
            <button
              onClick={() => navigate("/login")}
              style={{
                background: "rgba(255,255,255,0.1)",
                color: "#FFFFFF",
                border: "1px solid rgba(255,255,255,0.2)",
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

      {/* ── Editorial Footer ──────────────────────────────────────────────── */}
      <footer
        style={{
          borderTop: "1px solid #E2E4E9",
          padding: "50px 24px 36px",
          background: "#FAF9F6",
        }}
      >
        <div
          style={{
            maxWidth: "1100px",
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "36px",
            marginBottom: "40px",
          }}
        >
          <div>
            <div style={{ fontSize: "1.35rem", fontWeight: 900, color: "#0F172A", marginBottom: "10px", fontFamily: "'Space Grotesk', sans-serif" }}>
              ✦ syntropy
            </div>
            <p style={{ color: "#64748B", fontSize: "0.85rem", lineHeight: 1.6 }}>
              Open Finance personal intelligence platform for India. Built on the Reserve Bank of India (RBI) Account Aggregator framework.
            </p>
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "#0F172A", marginBottom: "12px" }}>Product</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.85rem" }}>
              <a href="#search-recall" style={{ color: "#475569", textDecoration: "none" }}>Search &amp; Recall</a>
              <a href="#bank-stack" style={{ color: "#475569", textDecoration: "none" }}>Multi-Bank Stack</a>
              <a href="#cleaner" style={{ color: "#475569", textDecoration: "none" }}>Clean Statements</a>
              <a href="#architecture" style={{ color: "#475569", textDecoration: "none" }}>No SMS Scraping</a>
            </div>
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "#0F172A", marginBottom: "12px" }}>Partnerships</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.85rem" }}>
              <a href="https://bridge.setu.co" target="_blank" rel="noreferrer" style={{ color: "#475569", textDecoration: "none" }}>Setu Bridge AA</a>
              <a href="https://sahamati.org.in" target="_blank" rel="noreferrer" style={{ color: "#475569", textDecoration: "none" }}>Sahamati Alliance</a>
              <a href="https://api.rebit.org.in" target="_blank" rel="noreferrer" style={{ color: "#475569", textDecoration: "none" }}>ReBIT AA Schemas</a>
            </div>
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "#0F172A", marginBottom: "12px" }}>Legal &amp; Trust</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.85rem", color: "#64748B" }}>
              <span>256-Bit Financial Grade Encryption</span>
              <span>RBI Master Directions (NBFC-AA)</span>
              <span>Zero Credential Storage Guarantee</span>
            </div>
          </div>
        </div>

        <div
          style={{
            maxWidth: "1100px",
            margin: "0 auto",
            paddingTop: "24px",
            borderTop: "1px solid #E2E4E9",
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "12px",
            color: "#94A3B8",
            fontSize: "0.8rem",
          }}
        >
          <div>© {new Date().getFullYear()} Syntropy Technologies. All rights reserved.</div>
          <div>Syntropy acts as a Technology Service Provider (TSP) on the RBI Account Aggregator network.</div>
        </div>
      </footer>
    </div>
  );
}
