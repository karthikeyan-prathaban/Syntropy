import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchFinancialData, getConsentStatus, getErrorMessage } from "../api/client";

const STEPS = [
  "Verifying consent approval…",
  "Fetching your financial data from Setu…",
  "Parsing transaction records…",
  "Building your analytics dashboard…",
  "Almost there…",
];

export default function ConsentCallbackPage() {
  const navigate = useNavigate();
  const [stepIdx, setStepIdx] = useState(0);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    const requestId = localStorage.getItem("syntropy_consent_request_id");
    if (!requestId) {
      setError("No consent session found. Please start again.");
      return;
    }

    async function waitForActive(id: string, attempts = 15) {
      for (let i = 0; i < attempts; i++) {
        const consent = await getConsentStatus(id);
        if (consent.status === "ACTIVE") return consent;
        await new Promise((r) => setTimeout(r, 3000));
      }
      throw new Error("Consent not active yet. Please approve in Setu and try again.");
    }

    async function process() {
      try {
        setStepIdx(0);
        await waitForActive(requestId!);
        setStepIdx(1);
        await fetchFinancialData(requestId!);
        setStepIdx(2);
        await new Promise((r) => setTimeout(r, 600));
        setStepIdx(3);
        await new Promise((r) => setTimeout(r, 600));
        setStepIdx(4);
        setDone(true);
        setTimeout(() => navigate("/dashboard"), 1200);
      } catch (err: unknown) {
        setError(getErrorMessage(err) || "Failed to fetch financial data");
      }
    }

    process();
  }, [navigate]);

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--bg-base)", padding: "24px",
    }}>
      <div className="glass fade-in" style={{ padding: "48px", textAlign: "center", maxWidth: "440px", width: "100%" }}>
        <div className="logo-mark grad-text" style={{ fontSize: "1.5rem", marginBottom: "24px", display: "block" }}>
          ✦ Syntropy
        </div>

        {error ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px", alignItems: "center" }}>
            <div style={{ fontSize: "2.5rem" }}>⚠️</div>
            <h3 style={{ fontSize: "1.1rem" }}>Something went wrong</h3>
            <div className="alert alert-error" style={{ textAlign: "left" }}>{error}</div>
            <div style={{ display: "flex", gap: "12px" }}>
              <button className="btn btn-primary btn-sm" onClick={() => {
                const id = localStorage.getItem("syntropy_consent_request_id");
                if (id) {
                  setError(""); setStepIdx(1);
                  fetchFinancialData(id)
                    .then(() => navigate("/dashboard"))
                    .catch((e) => setError(getErrorMessage(e)));
                } else {
                  navigate("/");
                }
              }}>
                Retry Fetch
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate("/")}>
                Back to Login
              </button>
            </div>
          </div>
        ) : done ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
            <div style={{ fontSize: "3rem" }}>✅</div>
            <h3 style={{ fontSize: "1.1rem" }}>All set! Redirecting…</h3>
          </div>
        ) : (
          <div>
            {/* Spinner */}
            <div style={{
              width: "56px", height: "56px", margin: "0 auto 24px",
              border: "3px solid rgba(16,185,129,0.2)", borderTopColor: "#10b981",
              borderRadius: "50%", animation: "spin 0.9s linear infinite",
            }} />
            <h3 style={{ fontSize: "1.1rem", marginBottom: "24px" }}>Processing your bank data</h3>

            {/* Step list */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", textAlign: "left" }}>
              {STEPS.map((step, i) => {
                const isPast = i < stepIdx;
                const isCurrent = i === stepIdx;
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: "12px", opacity: isPast || isCurrent ? 1 : 0.3, transition: "opacity 0.3s" }}>
                    <div style={{
                      width: "22px", height: "22px", borderRadius: "50%", flexShrink: 0,
                      background: isPast ? "var(--grad-brand)" : isCurrent ? "rgba(16,185,129,0.2)" : "rgba(255,255,255,0.05)",
                      border: isCurrent ? "2px solid var(--emerald)" : "2px solid transparent",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "0.7rem", fontWeight: 700, color: isPast ? "white" : "transparent",
                      animation: isCurrent ? "pulse-glow 1.5s infinite" : "none",
                      transition: "all 0.3s",
                    }}>
                      {isPast ? "✓" : ""}
                    </div>
                    <span style={{ fontSize: "0.875rem", color: isCurrent ? "var(--text-primary)" : isPast ? "var(--emerald)" : "var(--text-muted)", fontWeight: isCurrent ? 500 : 400 }}>
                      {step}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
