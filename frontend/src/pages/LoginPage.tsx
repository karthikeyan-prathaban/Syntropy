import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  demoLogin,
  getErrorMessage,
  loadMockData,
  login,
  signup,
} from "../api/client";

export default function LoginPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<"login" | "signup">("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Login fields
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Signup fields
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupMobile, setSignupMobile] = useState("");
  const [signupPassword, setSignupPassword] = useState("");

  // Demo fields
  const [demoName, setDemoName] = useState("");
  const [demoMobile, setDemoMobile] = useState("");

  function saveAuth(token: string, user: { id: number; name: string; email?: string }) {
    localStorage.setItem("syntropy_token", token);
    localStorage.setItem("syntropy_user", JSON.stringify(user));
    localStorage.setItem("syntropy_user_id", String(user.id));
    localStorage.setItem("syntropy_user_name", user.name);
  }

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await login(loginEmail, loginPassword);
      saveAuth(res.access_token, res.user);
      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleSignup(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await signup(signupName, signupEmail, signupMobile, signupPassword);
      saveAuth(res.access_token, res.user);
      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleDemoWithData() {
    if (!demoName || !demoMobile) {
      setError("Enter name and mobile for demo");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await demoLogin(demoName, demoMobile);
      saveAuth(res.access_token, res.user);
      await loadMockData(res.user.id);
      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      {/* Left panel */}
      <div className="auth-left">
        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ marginBottom: "48px" }}>
            <div className="logo-mark grad-text" style={{ fontSize: "1.8rem", marginBottom: "8px" }}>
              ✦ Syntropy
            </div>
            <div style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.9rem" }}>
              Open Finance Dashboard
            </div>
          </div>

          <h1 style={{ fontSize: "2.8rem", fontWeight: 900, lineHeight: 1.1, marginBottom: "20px", color: "#fff" }}>
            See your money.<br />
            <span className="grad-text">Grow your wealth.</span>
          </h1>
          <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "1rem", lineHeight: 1.7, marginBottom: "48px" }}>
            Connect your bank accounts securely via India's Account Aggregator framework. Get AI-powered insights to spend smarter.
          </p>

          {/* Feature pills */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {[
              { icon: "🔒", title: "RBI-regulated AA framework", sub: "Bank-grade encryption, consent-based" },
              { icon: "🤖", title: "AI spend advisor", sub: "Personalized tips to save more" },
              { icon: "📊", title: "Live analytics dashboard", sub: "Charts, trends, category breakdown" },
            ].map((f) => (
              <div key={f.title} style={{ display: "flex", gap: "14px", alignItems: "center" }}>
                <div style={{
                  width: "44px", height: "44px", background: "rgba(255,255,255,0.08)",
                  borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "1.2rem", flexShrink: 0, backdropFilter: "blur(8px)",
                }}>
                  {f.icon}
                </div>
                <div>
                  <div style={{ color: "rgba(255,255,255,0.9)", fontWeight: 600, fontSize: "0.9rem" }}>{f.title}</div>
                  <div style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.8rem" }}>{f.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div className="auth-right">
        <div className="auth-card fade-in">
          <div style={{ marginBottom: "32px" }}>
            <div className="logo-mark grad-text" style={{ fontSize: "1.5rem", display: "block", marginBottom: "6px" }}>
              ✦ Syntropy
            </div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 800 }}>
              {tab === "login" ? "Welcome back" : "Create account"}
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "4px" }}>
              {tab === "login" ? "Sign in to your financial dashboard" : "Start your financial journey"}
            </p>
          </div>

          {/* Tabs */}
          <div className="auth-tabs">
            <button className={`auth-tab ${tab === "login" ? "active" : ""}`} onClick={() => { setTab("login"); setError(""); }}>
              Sign In
            </button>
            <button className={`auth-tab ${tab === "signup" ? "active" : ""}`} onClick={() => { setTab("signup"); setError(""); }}>
              Sign Up
            </button>
          </div>

          {error && <div className="alert alert-error" style={{ marginBottom: "16px" }}>⚠ {error}</div>}

          {/* Login form */}
          {tab === "login" && (
            <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div className="input-group">
                <label className="input-label">Email address</label>
                <input className="input" type="email" required placeholder="you@example.com"
                  value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Password</label>
                <input className="input" type="password" required placeholder="••••••••"
                  value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} />
              </div>
              <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
                {loading ? <span className="spin">⟳</span> : "Sign in →"}
              </button>
            </form>
          )}

          {/* Signup form */}
          {tab === "signup" && (
            <form onSubmit={handleSignup} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div className="input-group">
                <label className="input-label">Full name</label>
                <input className="input" required placeholder="Karthikeyan P"
                  value={signupName} onChange={(e) => setSignupName(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Email address</label>
                <input className="input" type="email" required placeholder="you@example.com"
                  value={signupEmail} onChange={(e) => setSignupEmail(e.target.value)} />
              </div>
              <div className="input-group">
                <label className="input-label">Mobile number</label>
                <input className="input" type="tel" required placeholder="9876543210"
                  value={signupMobile} onChange={(e) => setSignupMobile(e.target.value)} />
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Used for AA consent verification</span>
              </div>
              <div className="input-group">
                <label className="input-label">Password</label>
                <input className="input" type="password" required minLength={6} placeholder="Min 6 characters"
                  value={signupPassword} onChange={(e) => setSignupPassword(e.target.value)} />
              </div>
              <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
                {loading ? <span className="spin">⟳</span> : "Create account →"}
              </button>
            </form>
          )}

          {/* Demo section */}
          <div className="divider-text" style={{ margin: "24px 0" }}>or try with demo data</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <input className="input" placeholder="Your name" style={{ fontSize: "0.85rem" }}
                value={demoName} onChange={(e) => setDemoName(e.target.value)} />
              <input className="input" placeholder="Mobile no." type="tel" style={{ fontSize: "0.85rem" }}
                value={demoMobile} onChange={(e) => setDemoMobile(e.target.value)} />
            </div>
            <button className="btn btn-secondary btn-full" onClick={handleDemoWithData} disabled={loading} type="button">
              🎯 Preview with Demo Data
            </button>
          </div>

          <p style={{ color: "var(--text-muted)", fontSize: "0.72rem", textAlign: "center", marginTop: "20px", lineHeight: 1.6 }}>
            Data is fetched via India's RBI-regulated Account Aggregator framework with your explicit consent. We never store raw credentials.
          </p>
        </div>
      </div>
    </div>
  );
}
