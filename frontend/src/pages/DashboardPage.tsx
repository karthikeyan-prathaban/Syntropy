import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from "recharts";
import {
  BankAccount, DashboardData, Transaction,
  createConsentForUser, fetchFinancialData, getConsentStatus,
  getDashboard, getMyDashboard, getMyTransactions, loadMockData,
} from "../api/client";
import BankOnboardingModal from "../components/BankOnboardingModal";

// ── Colors ─────────────────────────────────────────────────────────────────
const PALETTE = ["#10b981", "#06b6d4", "#8b5cf6", "#f59e0b", "#ef4444", "#ec4899", "#3b82f6", "#f97316"];

function fmt(n: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}
function fmtShort(n: number) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}K`;
  return `₹${n.toFixed(0)}`;
}

// ── Sub-components ──────────────────────────────────────────────────────────

function HealthRing({ score }: { score: number }) {
  const r = 54; const c = 2 * Math.PI * r;
  const fill = (score / 100) * c;
  const color = score >= 70 ? "#10b981" : score >= 45 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
      <svg width={130} height={130} style={{ overflow: "visible" }}>
        <circle cx={65} cy={65} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={10} />
        <circle cx={65} cy={65} r={r} fill="none" stroke={color} strokeWidth={10}
          strokeDasharray={`${fill} ${c}`}
          strokeDashoffset={0}
          strokeLinecap="round"
          transform="rotate(-90 65 65)"
          style={{ transition: "stroke-dasharray 1s ease", filter: `drop-shadow(0 0 6px ${color})` }}
        />
        <text x={65} y={62} textAnchor="middle" fill={color} fontSize={24} fontWeight={800} fontFamily="Inter">
          {score}
        </text>
        <text x={65} y={78} textAnchor="middle" fill="#475569" fontSize={10} fontFamily="Inter">
          / 100
        </text>
      </svg>
      <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontWeight: 500 }}>Financial Health</span>
    </div>
  );
}

function StatCard({ label, value, sub, accent = "#f8fafc", icon, delay = "0s" }: {
  label: string; value: string; sub?: string; accent?: string; icon: string; delay?: string;
}) {
  return (
    <div className="glass glass-hover stat-card fade-in" style={{ animationDelay: delay }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
        <span className="stat-label">{label}</span>
        <span style={{ fontSize: "1.3rem" }}>{icon}</span>
      </div>
      <div className="stat-value" style={{ color: accent }}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function Sidebar({ active, onNav, user, onLogout }: {
  active: string; onNav: (p: string) => void;
  user: { name: string; email?: string; avatar_initials?: string }; onLogout: () => void;
}) {
  const nav = [
    { id: "overview", icon: "◈", label: "Overview" },
    { id: "analytics", icon: "⬡", label: "Analytics" },
    { id: "transactions", icon: "↕", label: "Transactions" },
    { id: "insights", icon: "✦", label: "AI Insights" },
    { id: "accounts", icon: "⬛", label: "Accounts" },
  ];
  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark grad-text">✦ Syntropy</div>
        <div style={{ color: "var(--text-muted)", fontSize: "0.72rem", marginTop: "2px" }}>Open Finance</div>
      </div>
      <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: "4px" }}>
        {nav.map((item) => (
          <button key={item.id} className={`nav-item ${active === item.id ? "active" : ""}`}
            onClick={() => onNav(item.id)}>
            <span style={{ fontSize: "1rem", width: "18px", textAlign: "center" }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>
      <div style={{ borderTop: "1px solid var(--border)", paddingTop: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px", marginBottom: "8px" }}>
          <div className="avatar">{user.avatar_initials || user.name.slice(0, 2).toUpperCase()}</div>
          <div style={{ overflow: "hidden" }}>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user.name}</div>
            {user.email && <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user.email}</div>}
          </div>
        </div>
        <button className="nav-item" onClick={onLogout} style={{ width: "100%", color: "var(--text-muted)" }}>
          <span>⇥</span> Sign out
        </button>
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="glass" style={{ padding: "12px 16px", fontSize: "0.82rem", minWidth: "160px" }}>
        {label && <div style={{ color: "var(--text-muted)", marginBottom: "8px" }}>{label}</div>}
        {payload.map((p: any, i: number) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: "20px", color: p.color }}>
            <span>{p.name}</span><span style={{ fontWeight: 700 }}>{fmt(p.value)}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// ── Main Dashboard ──────────────────────────────────────────────────────────

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<"overview" | "analytics" | "transactions" | "insights" | "accounts">("overview");
  const [searchQ, setSearchQ] = useState("");
  const [filterCat, setFilterCat] = useState("");
  const [filterType, setFilterType] = useState("");
  const [consentLoading, setConsentLoading] = useState(false);
  const [consentMsg, setConsentMsg] = useState("");
  const [showOnboardingModal, setShowOnboardingModal] = useState(false);
  const [successToast, setSuccessToast] = useState("");

  const userId = Number(localStorage.getItem("syntropy_user_id"));

  useEffect(() => {
    if (!userId) { navigate("/"); return; }

    const token = localStorage.getItem("syntropy_token");
    const load = token
      ? getMyDashboard().catch(() => getDashboard(userId))
      : getDashboard(userId);

    load
      .then((d) => { setData(d); })
      .catch(() => navigate("/"))
      .finally(() => setLoading(false));

    getMyTransactions({ limit: 500 })
      .catch(() => [])
      .then(setAllTransactions);
  }, [userId, navigate]);

  function handleLogout() {
    ["syntropy_token", "syntropy_user", "syntropy_user_id", "syntropy_user_name",
      "syntropy_consent_request_id"].forEach((k) => localStorage.removeItem(k));
    navigate("/");
  }

  async function startConsentFlow() {
    setConsentLoading(true);
    setConsentMsg("");
    try {
      const consent = await createConsentForUser(userId);
      if (consent && consent.consent_url) {
        localStorage.setItem("syntropy_consent_request_id", consent.request_id);
        window.location.href = consent.consent_url;
        return;
      }
      setShowOnboardingModal(true);
    } catch {
      setShowOnboardingModal(true);
    } finally {
      setConsentLoading(false);
    }
  }

  async function handleOnboardingSuccess(bankName: string) {
    setShowOnboardingModal(false);
    setConsentMsg("");
    setLoading(true);
    try {
      const refreshed = await getDashboard(userId);
      setData(refreshed);
      const txns = await getMyTransactions({ limit: 500 }).catch(() => []);
      setAllTransactions(txns);
      setSuccessToast(`✓ Successfully verified OTP & linked ${bankName}! Real-time expenses loaded.`);
      setTimeout(() => setSuccessToast(""), 4000);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  if (loading || !data) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: "48px", height: "48px", border: "3px solid rgba(16,185,129,0.2)", borderTopColor: "#10b981", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
          <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Loading your dashboard…</div>
        </div>
      </div>
    );
  }

  // Filtered transactions
  const txns = (allTransactions.length > 0 ? allTransactions : data.recent_transactions).filter((t) => {
    const q = searchQ.toLowerCase();
    if (q && !t.narration.toLowerCase().includes(q) && !t.category.toLowerCase().includes(q)) return false;
    if (filterCat && t.category !== filterCat) return false;
    if (filterType && t.txn_type !== filterType) return false;
    return true;
  });

  const categories = Array.from(new Set((allTransactions.length > 0 ? allTransactions : data.recent_transactions).map((t) => t.category)));

  const consentActive = data.consent_status === "ACTIVE";

  return (
    <div className="app-layout">
      <div className="glow-orb glow-orb-1" />
      <div className="glow-orb glow-orb-2" />

      <Sidebar
        active={page}
        onNav={(p) => setPage(p as any)}
        user={data.user}
        onLogout={handleLogout}
      />

      <main className="main-content">
        {/* ── Overview ───────────────────────────────────────────── */}
        {page === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h1 className="page-title">Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}, {data.user.name.split(" ")[0]} 👋</h1>
                <p className="page-subtitle">Here's your financial snapshot for {new Date().toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</p>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                {!consentActive && (
                  <button className="btn btn-primary btn-sm" onClick={startConsentFlow} disabled={consentLoading}>
                    {consentLoading ? <span className="spin">⟳</span> : "🔗 Link Bank Account"}
                  </button>
                )}
                <button className="btn btn-secondary btn-sm" onClick={async () => {
                  setLoading(true);
                  try { await loadMockData(userId); const d = await getDashboard(userId); setData(d); } catch { }
                  setLoading(false);
                }}>
                  ↺ Refresh Demo
                </button>
              </div>
            </div>

            {successToast && (
              <div style={{ background: "#ECFDF5", color: "#065F46", padding: "12px 18px", borderRadius: "10px", border: "1px solid #A7F3D0", fontWeight: 700, fontSize: "0.9rem" }}>
                {successToast}
              </div>
            )}

            {consentMsg && <div className="alert alert-error">{consentMsg}</div>}

            {/* Consent banner with OTP link button */}
            <div className={`consent-banner ${consentActive ? "active" : "none"}`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span>{consentActive ? "✓" : "⚠"}</span>
                <span>
                  {consentActive
                    ? "Bank data synced via Setu Account Aggregator. Consent active."
                    : "No active bank consent. Link your bank account with OTP to see real transaction data."}
                </span>
              </div>
              {!consentActive && (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setShowOnboardingModal(true)}
                  style={{ whiteSpace: "nowrap" }}
                >
                  Verify OTP &amp; Link →
                </button>
              )}
            </div>

            {/* Zero balance onboarding callout */}
            {!consentActive && data.total_balance === 0 && (
              <div
                style={{
                  background: "#EFF6FF",
                  border: "1.5px dashed #3B82F6",
                  borderRadius: "16px",
                  padding: "24px 28px",
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "16px",
                }}
              >
                <div>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 800, color: "#1E40AF", marginBottom: "4px" }}>
                    🚀 Onboard Your Bank Account with OTP
                  </h3>
                  <p style={{ color: "#2563EB", fontSize: "0.85rem", margin: 0, fontWeight: 500 }}>
                    Select HDFC, SBI, ICICI, or Axis Bank. Verify with 6-digit OTP to decrypt your real-time expenses and financial health score.
                  </p>
                </div>
                <button
                  onClick={() => setShowOnboardingModal(true)}
                  style={{
                    background: "#2563EB",
                    color: "#FFFFFF",
                    border: "none",
                    padding: "12px 24px",
                    borderRadius: "10px",
                    fontWeight: 700,
                    fontSize: "0.9rem",
                    cursor: "pointer",
                    boxShadow: "0 4px 14px rgba(37, 99, 235, 0.25)",
                    whiteSpace: "nowrap",
                  }}
                >
                  Start Bank Onboarding ⚡
                </button>
              </div>
            )}

            {/* Stat cards */}
            <div className="grid-4">
              <StatCard label="Total Balance" value={fmt(data.total_balance)} icon="◈" accent="var(--text-primary)" delay="0s" />
              <StatCard label="Monthly Income" value={fmt(data.total_income)} sub="This month" icon="↑" accent="var(--emerald-light)" delay="0.05s" />
              <StatCard label="Monthly Expense" value={fmt(data.total_expense)} sub={`${100 - data.savings_rate}% of income`} icon="↓" accent="#fca5a5" delay="0.1s" />
              <StatCard label="Savings Rate" value={`${data.savings_rate}%`} sub="Target: 20%" icon="★" accent={data.savings_rate >= 20 ? "var(--emerald-light)" : data.savings_rate >= 10 ? "#fcd34d" : "#fca5a5"} delay="0.15s" />
            </div>

            {/* Charts row */}
            <div className="grid-2">
              {/* Pie chart */}
              <div className="glass chart-container fade-in stagger-3">
                <div className="chart-title">Spending by Category</div>
                {data.category_breakdown.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie data={data.category_breakdown} dataKey="amount" nameKey="category"
                        cx="50%" cy="50%" outerRadius={85} innerRadius={45}
                        paddingAngle={2}>
                        {data.category_breakdown.map((_, i) => (
                          <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" iconSize={8}
                        formatter={(v) => <span style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>{v}</span>} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
                    No spending data yet. Link your bank account.
                  </div>
                )}
              </div>

              {/* Bar chart */}
              <div className="glass chart-container fade-in stagger-4">
                <div className="chart-title">Income vs Expense (6 months)</div>
                {data.monthly_trend.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={data.monthly_trend} barCategoryGap="30%">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" tick={{ fill: "#475569", fontSize: 11 }} />
                      <YAxis tickFormatter={fmtShort} tick={{ fill: "#475569", fontSize: 11 }} width={60} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" iconSize={8}
                        formatter={(v) => <span style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>{v.charAt(0).toUpperCase() + v.slice(1)}</span>} />
                      <Bar dataKey="income" name="Income" fill="#10b981" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="expense" name="Expense" fill="#ef4444" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
                    No trend data yet.
                  </div>
                )}
              </div>
            </div>

            {/* Bottom row: health score + top recommendations */}
            <div className="grid-2">
              <div className="glass" style={{ padding: "24px", display: "flex", alignItems: "center", gap: "32px" }}>
                <HealthRing score={data.health_score} />
                <div>
                  <h3 style={{ marginBottom: "8px" }}>
                    {data.health_score >= 70 ? "Excellent shape! 🎉" : data.health_score >= 45 ? "Room to improve 📈" : "Needs attention ⚠"}
                  </h3>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", lineHeight: 1.6 }}>
                    {data.health_score >= 70
                      ? "Your savings rate and balance are strong. Keep it up!"
                      : data.health_score >= 45
                      ? "Focus on savings rate and reducing top spending categories."
                      : "Immediate action needed — review budget and build an emergency fund."}
                  </p>
                  <div style={{ marginTop: "12px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <span className={`badge ${data.savings_rate >= 20 ? "badge-success" : "badge-danger"}`}>
                      Savings: {data.savings_rate}%
                    </span>
                    <span className={`badge ${consentActive ? "badge-success" : "badge-warn"}`}>
                      {consentActive ? "✓ AA Connected" : "⚠ No AA Data"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Top 2 AI recommendations */}
              <div className="glass" style={{ padding: "24px" }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: "16px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  ✦ AI Recommendations
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {data.recommendations.slice(0, 3).map((rec, i) => (
                    <div key={i} className="rec-card" style={{ padding: "14px", background: "rgba(255,255,255,0.02)", borderRadius: "10px", border: "1px solid var(--border)" }}>
                      <div className={`rec-dot ${rec.priority}`} />
                      <div>
                        <div className="rec-title">{rec.title}</div>
                        <div className="rec-desc">{rec.description}</div>
                        {rec.saving_potential ? (
                          <div className="rec-saving">💰 Save ~{fmt(rec.saving_potential)}/month</div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => setPage("insights")} style={{ marginTop: "12px" }}>
                  View all insights →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Analytics ──────────────────────────────────────────── */}
        {page === "analytics" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div className="page-header">
              <h1 className="page-title">Analytics</h1>
              <p className="page-subtitle">Deep-dive into your spending patterns</p>
            </div>

            {/* Category breakdown cards */}
            <div style={{ fontWeight: 600, fontSize: "0.95rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
              Spending Breakdown
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {data.category_breakdown.map((cat, i) => (
                <div key={cat.category} className="glass fade-in" style={{ padding: "16px 20px", animationDelay: `${i * 0.05}s` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: PALETTE[i % PALETTE.length] }} />
                      <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{cat.category}</span>
                      {cat.count && <span className="badge badge-neutral">{cat.count} txns</span>}
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>{fmt(cat.amount)}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{cat.percentage}% of total</div>
                    </div>
                  </div>
                  <div style={{ height: "4px", background: "rgba(255,255,255,0.06)", borderRadius: "2px", overflow: "hidden" }}>
                    <div style={{
                      height: "100%", borderRadius: "2px",
                      background: PALETTE[i % PALETTE.length],
                      width: `${cat.percentage}%`,
                      transition: "width 1s ease",
                      boxShadow: `0 0 8px ${PALETTE[i % PALETTE.length]}60`,
                    }} />
                  </div>
                </div>
              ))}
              {data.category_breakdown.length === 0 && (
                <div className="glass" style={{ padding: "48px", textAlign: "center", color: "var(--text-muted)" }}>
                  No spending data yet. Link your bank account to see analytics.
                </div>
              )}
            </div>

            {/* Monthly detailed chart */}
            <div className="glass chart-container">
              <div className="chart-title">Monthly Income vs Expense Trend</div>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={data.monthly_trend} barCategoryGap="25%">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fill: "#475569", fontSize: 11 }} />
                  <YAxis tickFormatter={fmtShort} tick={{ fill: "#475569", fontSize: 11 }} width={65} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend iconType="circle" iconSize={8}
                    formatter={(v) => <span style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>{v.charAt(0).toUpperCase() + v.slice(1)}</span>} />
                  <Bar dataKey="income" name="Income" fill="#10b981" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expense" name="Expense" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ── Transactions ────────────────────────────────────────── */}
        {page === "transactions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div className="page-header">
              <h1 className="page-title">Transactions</h1>
              <p className="page-subtitle">{txns.length} records shown</p>
            </div>

            {/* Filters */}
            <div className="glass" style={{ padding: "16px 20px", display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
              <input className="input" placeholder="🔍 Search narration or category…"
                style={{ maxWidth: "280px", flex: "1" }}
                value={searchQ} onChange={(e) => setSearchQ(e.target.value)} />
              <select className="input" style={{ maxWidth: "180px" }}
                value={filterCat} onChange={(e) => setFilterCat(e.target.value)}>
                <option value="">All categories</option>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="input" style={{ maxWidth: "140px" }}
                value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                <option value="">All types</option>
                <option value="CREDIT">Credit</option>
                <option value="DEBIT">Debit</option>
              </select>
              {(searchQ || filterCat || filterType) && (
                <button className="btn btn-ghost btn-sm" onClick={() => { setSearchQ(""); setFilterCat(""); setFilterType(""); }}>
                  Clear ✕
                </button>
              )}
            </div>

            <div className="glass" style={{ overflow: "hidden" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Category</th>
                    <th>Mode</th>
                    <th>Account</th>
                    <th style={{ textAlign: "right" }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {txns.slice(0, 200).map((t) => (
                    <tr key={t.id}>
                      <td style={{ color: "var(--text-muted)", whiteSpace: "nowrap", fontSize: "0.82rem" }}>
                        {new Date(t.transaction_timestamp).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                      </td>
                      <td style={{ color: "var(--text-primary)", maxWidth: "250px" }}>
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {t.narration || "—"}
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-neutral">{t.category}</span>
                      </td>
                      <td style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>{t.mode}</td>
                      <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{t.masked_acc_number || "—"}</td>
                      <td style={{ textAlign: "right", fontWeight: 700, whiteSpace: "nowrap" }}>
                        <span style={{ color: t.txn_type === "CREDIT" ? "var(--emerald-light)" : "#fca5a5" }}>
                          {t.txn_type === "CREDIT" ? "+" : "−"}{fmt(t.amount)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {txns.length === 0 && (
                <div style={{ padding: "48px", textAlign: "center", color: "var(--text-muted)" }}>
                  No transactions found matching your filters.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── AI Insights ─────────────────────────────────────────── */}
        {page === "insights" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div className="page-header">
              <h1 className="page-title">✦ AI Insights</h1>
              <p className="page-subtitle">Personalized recommendations to improve your financial health</p>
            </div>

            {/* Summary banner */}
            <div className="glass" style={{
              padding: "24px", display: "flex", gap: "32px", alignItems: "center",
              background: "linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(6,182,212,0.05) 100%)",
              borderColor: "rgba(16,185,129,0.2)",
            }}>
              <HealthRing score={data.health_score} />
              <div style={{ flex: 1 }}>
                <h3 style={{ marginBottom: "8px", fontSize: "1.1rem" }}>
                  Total potential savings: <span className="grad-text">
                    {fmt(data.recommendations.reduce((s, r) => s + (r.saving_potential || 0), 0))}/month
                  </span>
                </h3>
                <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", lineHeight: 1.6 }}>
                  Based on your transaction patterns, here are {data.recommendations.length} personalized recommendations.
                  {data.health_score < 70 && " Addressing high-priority items first can significantly improve your score."}
                </p>
                <div style={{ display: "flex", gap: "8px", marginTop: "12px", flexWrap: "wrap" }}>
                  {["high", "medium", "low"].map((p) => {
                    const count = data.recommendations.filter((r) => r.priority === p).length;
                    if (!count) return null;
                    const cls = p === "high" ? "badge-danger" : p === "medium" ? "badge-warn" : "badge-success";
                    return <span key={p} className={`badge ${cls}`}>{count} {p} priority</span>;
                  })}
                </div>
              </div>
            </div>

            {/* All recommendations */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {data.recommendations.map((rec, i) => (
                <div key={i} className="glass glass-hover fade-in" style={{ animationDelay: `${i * 0.06}s` }}>
                  <div className="rec-card">
                    <div className={`rec-dot ${rec.priority}`} style={{ marginTop: "2px" }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
                        <div className="rec-title" style={{ fontSize: "1rem" }}>{rec.title}</div>
                        <span className={`badge ${rec.priority === "high" ? "badge-danger" : rec.priority === "medium" ? "badge-warn" : "badge-success"}`}
                          style={{ flexShrink: 0 }}>
                          {rec.priority}
                        </span>
                      </div>
                      <div className="rec-desc" style={{ fontSize: "0.875rem", marginTop: "8px" }}>{rec.description}</div>
                      {rec.saving_potential ? (
                        <div style={{ marginTop: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                          <div style={{
                            background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)",
                            borderRadius: "8px", padding: "6px 12px", fontSize: "0.82rem", fontWeight: 600, color: "var(--emerald-light)",
                          }}>
                            💰 Potential saving: {fmt(rec.saving_potential)}/month
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                            = {fmt(rec.saving_potential * 12)}/year
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Accounts ────────────────────────────────────────────── */}
        {page === "accounts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h1 className="page-title">Bank Accounts</h1>
                <p className="page-subtitle">Your linked accounts via Account Aggregator</p>
              </div>
              <button className="btn btn-primary" onClick={startConsentFlow} disabled={consentLoading}>
                {consentLoading ? <span className="spin">⟳</span> : "🔗 Link New Account"}
              </button>
            </div>

            {consentMsg && <div className="alert alert-error">{consentMsg}</div>}

            {/* Consent status */}
            <div className={`consent-banner ${consentActive ? "active" : "none"}`}>
              {consentActive
                ? "✓ Account Aggregator consent is ACTIVE. Your data is synced via Setu."
                : "⚠ No active consent. Click 'Link New Account' to connect your bank via India's AA framework."}
            </div>

            {/* Account cards */}
            {data.accounts.length > 0 ? (
              <div className="grid-2">
                {data.accounts.map((acc, i) => (
                  <div key={acc.id} className="glass glass-hover account-card fade-in" style={{ animationDelay: `${i * 0.08}s` }}>
                    <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                      <div className="account-icon">🏦</div>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{acc.masked_acc_number}</div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
                          {acc.account_type} • {acc.fip_id || "Bank"}
                        </div>
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontWeight: 800, fontSize: "1.3rem", color: "var(--emerald-light)" }}>{fmt(acc.current_balance)}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{acc.currency} balance</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="glass" style={{ padding: "64px", textAlign: "center" }}>
                <div style={{ fontSize: "3rem", marginBottom: "16px" }}>🏦</div>
                <h3 style={{ marginBottom: "8px" }}>No accounts linked</h3>
                <p style={{ color: "var(--text-muted)", marginBottom: "24px", fontSize: "0.9rem" }}>
                  Connect your bank account via India's RBI-regulated Account Aggregator framework to see your balance and transactions.
                </p>
                <button className="btn btn-primary" onClick={startConsentFlow}>
                  🔗 Link Bank Account
                </button>
                <p style={{ color: "var(--text-muted)", fontSize: "0.78rem", marginTop: "16px" }}>
                  Supports: HDFC, ICICI, SBI, Axis, Kotak, and 40+ banks via Setu AA
                </p>
              </div>
            )}

            {/* AA explanation */}
            <div className="glass" style={{ padding: "24px", background: "rgba(6,182,212,0.04)", borderColor: "rgba(6,182,212,0.15)" }}>
              <h4 style={{ marginBottom: "12px", fontSize: "0.95rem" }}>ℹ️ How Account Aggregator works</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
                {[
                  { step: "1", title: "You consent", desc: "Approve data sharing via Setu's AA interface" },
                  { step: "2", title: "Bank shares data", desc: "Your bank sends encrypted transaction data" },
                  { step: "3", title: "You see insights", desc: "Syntropy analyzes and shows your dashboard" },
                ].map((s) => (
                  <div key={s.step} style={{ textAlign: "center" }}>
                    <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "var(--grad-brand)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 8px", fontSize: "0.85rem", fontWeight: 700 }}>{s.step}</div>
                    <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "4px" }}>{s.title}</div>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.78rem", lineHeight: 1.5 }}>{s.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {showOnboardingModal && (
        <BankOnboardingModal
          userId={userId}
          userName={data.user.name}
          userMobile={data.user.mobile}
          onClose={() => setShowOnboardingModal(false)}
          onSuccess={handleOnboardingSuccess}
        />
      )}
    </div>
  );
}
