import { useState, useEffect, useRef } from "react";
import { onboardBankWithOtp } from "../api/client";
import { Analytics } from "../utils/analytics";

interface BankOption {
  id: string;
  name: string;
  code: string;
  icon: string;
  color: string;
  fip: string;
}

const AVAILABLE_BANKS: BankOption[] = [
  { id: "hdfc", name: "HDFC Bank", code: "HDFC", icon: "🏛️", color: "#0A2D67", fip: "HDFC-FIP" },
  { id: "sbi", name: "State Bank of India", code: "SBIN", icon: "🇮🇳", color: "#064E3B", fip: "SBIN-FIP" },
  { id: "icici", name: "ICICI Bank", code: "ICIC", icon: "🏦", color: "#C2410C", fip: "ICIC-FIP" },
  { id: "axis", name: "Axis Bank", code: "UTIB", icon: "🏛️", color: "#991B1B", fip: "UTIB-FIP" },
  { id: "kotak", name: "Kotak Mahindra", code: "KKBK", icon: "🏦", color: "#B91C1C", fip: "KKBK-FIP" },
  { id: "zerodha", name: "Zerodha Broking", code: "ZRDH", icon: "📈", color: "#18181B", fip: "ZRDH-FIP" },
];

interface BankOnboardingModalProps {
  userId: number;
  userName: string;
  userMobile?: string;
  onClose: () => void;
  onSuccess: (bankName: string) => void;
}

export default function BankOnboardingModal({
  userId,
  userName,
  userMobile = "9876543210",
  onClose,
  onSuccess,
}: BankOnboardingModalProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedBank, setSelectedBank] = useState<BankOption>(AVAILABLE_BANKS[0]);
  const [mobile, setMobile] = useState(userMobile || "9876543210");
  const [otpDigits, setOtpDigits] = useState<string[]>(["1", "2", "3", "4", "5", "6"]);
  const [timer, setTimer] = useState(28);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Step 4 progress indicators
  const [syncPhase, setSyncPhase] = useState(0);

  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    let interval: any;
    if (step === 2 && timer > 0) {
      interval = setInterval(() => setTimer((t) => t - 1), 1000);
    }
    return () => clearInterval(interval);
  }, [step, timer]);

  function handleOtpChange(index: number, val: string) {
    const cleaned = val.replace(/\D/g, "");
    if (!cleaned && val === "") {
      const next = [...otpDigits];
      next[index] = "";
      setOtpDigits(next);
      return;
    }
    const lastChar = cleaned.slice(-1);
    const next = [...otpDigits];
    next[index] = lastChar;
    setOtpDigits(next);

    // Auto-advance
    if (index < 5 && lastChar) {
      otpInputRefs.current[index + 1]?.focus();
    }
  }

  function handleOtpKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
    }
  }

  async function handleVerifyOtpAndProceed() {
    const fullOtp = otpDigits.join("");
    if (fullOtp.length !== 6) {
      setError("Please enter the complete 6-digit OTP code.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      setStep(3); // Show discovered accounts
      Analytics.demoInteracted("otp_verified", { bank: selectedBank.name });
    } catch (err: any) {
      setError(err?.message || "Failed to verify OTP.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFinalizeConsent() {
    setLoading(true);
    setError("");
    setStep(4); // Start animated sync

    try {
      // Animated progress stages
      setSyncPhase(1);
      await new Promise((r) => setTimeout(r, 600));
      setSyncPhase(2);
      await new Promise((r) => setTimeout(r, 600));
      setSyncPhase(3);

      const fullOtp = otpDigits.join("") || "123456";
      await onboardBankWithOtp({
        user_id: userId,
        bank_id: selectedBank.id,
        mobile: mobile,
        otp: fullOtp,
        selected_accounts: ["acc_savings", "acc_salary"],
      });

      setSyncPhase(4);
      await new Promise((r) => setTimeout(r, 500));
      onSuccess(selectedBank.name);
    } catch (err: any) {
      setError(err?.message || "Failed to link bank account. Please retry.");
      setStep(3);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
    >
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: "24px",
          width: "100%",
          maxWidth: "540px",
          border: "1px solid #E2E4E9",
          boxShadow: "0 25px 60px -15px rgba(15, 23, 42, 0.2)",
          overflow: "hidden",
          position: "relative",
          animation: "slideInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) both",
        }}
      >
        {/* Header Bar */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #E2E4E9",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "#FAF9F6",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "1.3rem" }}>🏛️</span>
            <div>
              <div style={{ fontWeight: 800, fontSize: "1.05rem", color: "#0F172A", fontFamily: "'Space Grotesk', sans-serif" }}>
                Link Bank Account via AA
              </div>
              <div style={{ fontSize: "0.74rem", color: "#059669", fontWeight: 600 }}>
                ● Reserve Bank of India (RBI) Regulated Consent
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: "1.2rem",
              color: "#94A3B8",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            ✕
          </button>
        </div>

        {/* Step Progress Tracker */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            padding: "12px 24px",
            background: "#F8FAFC",
            borderBottom: "1px solid #E2E4E9",
            fontSize: "0.76rem",
            fontWeight: 700,
            color: "#64748B",
            gap: "8px",
          }}
        >
          <span style={{ color: step >= 1 ? "#2563EB" : "#94A3B8" }}>1. Bank</span>
          <span>→</span>
          <span style={{ color: step >= 2 ? "#2563EB" : "#94A3B8" }}>2. Verify OTP</span>
          <span>→</span>
          <span style={{ color: step >= 3 ? "#2563EB" : "#94A3B8" }}>3. Select Accounts</span>
          <span>→</span>
          <span style={{ color: step >= 4 ? "#059669" : "#94A3B8" }}>4. Ingest Data</span>
        </div>

        {/* Error Banner */}
        {error && (
          <div style={{ background: "#FFF1F2", color: "#9F1239", padding: "10px 24px", fontSize: "0.84rem", fontWeight: 600, borderBottom: "1px solid #FECDD3" }}>
            ⚠️ {error}
          </div>
        )}

        {/* Modal Body */}
        <div style={{ padding: "28px" }}>
          {/* ── STEP 1: Select Bank & Mobile ── */}
          {step === 1 && (
            <div>
              <div style={{ marginBottom: "20px" }}>
                <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  SELECT YOUR PRIMARY BANK (FIP):
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                  {AVAILABLE_BANKS.map((bank) => {
                    const isSelected = selectedBank.id === bank.id;
                    return (
                      <button
                        key={bank.id}
                        type="button"
                        onClick={() => setSelectedBank(bank)}
                        style={{
                          background: isSelected ? "#EFF6FF" : "#FFFFFF",
                          border: `1.5px solid ${isSelected ? "#2563EB" : "#E2E4E9"}`,
                          borderRadius: "12px",
                          padding: "12px 8px",
                          cursor: "pointer",
                          textAlign: "center",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ fontSize: "1.4rem", marginBottom: "4px" }}>{bank.icon}</div>
                        <div style={{ fontSize: "0.8rem", fontWeight: 700, color: isSelected ? "#1E40AF" : "#0F172A" }}>
                          {bank.name}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ marginBottom: "20px" }}>
                <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 700, color: "#334155", marginBottom: "6px" }}>
                  BANK REGISTERED MOBILE NUMBER:
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <span
                    style={{
                      background: "#F1F5F9",
                      border: "1px solid #E2E4E9",
                      borderRadius: "8px",
                      padding: "10px 14px",
                      fontWeight: 600,
                      fontSize: "0.9rem",
                      color: "#475569",
                    }}
                  >
                    +91
                  </span>
                  <input
                    type="tel"
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value.replace(/\D/g, "").slice(0, 10))}
                    placeholder="Enter 10 digit mobile"
                    style={{
                      flex: 1,
                      border: "1px solid #E2E4E9",
                      borderRadius: "8px",
                      padding: "10px 14px",
                      fontSize: "0.92rem",
                      fontWeight: 600,
                      color: "#0F172A",
                      outline: "none",
                    }}
                  />
                </div>
                <div style={{ fontSize: "0.75rem", color: "#64748B", marginTop: "4px" }}>
                  AA Virtual Address: <strong>{mobile || "9876543210"}@onemoney</strong>
                </div>
              </div>

              {/* Consent Terms Summary Card */}
              <div
                style={{
                  background: "#FAF9F6",
                  border: "1px solid #E2E4E9",
                  borderRadius: "12px",
                  padding: "14px",
                  fontSize: "0.8rem",
                  color: "#475569",
                  marginBottom: "24px",
                  lineHeight: 1.5,
                }}
              >
                <div>🔒 <strong>Purpose:</strong> Personal Finance &amp; Expense Analytics (Code 101)</div>
                <div>⏱️ <strong>Duration:</strong> 12 Months • <strong>Frequency:</strong> Periodic Monthly</div>
                <div>🛡️ <strong>Safety:</strong> Read-only encrypted data. Syntropy cannot move or withdraw funds.</div>
              </div>

              <button
                type="button"
                onClick={() => {
                  if (mobile.length < 10) {
                    setError("Please enter a valid 10-digit mobile number.");
                    return;
                  }
                  setError("");
                  setTimer(28);
                  setStep(2);
                }}
                style={{
                  width: "100%",
                  background: "#0F172A",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "14px",
                  borderRadius: "12px",
                  fontWeight: 700,
                  fontSize: "0.95rem",
                  cursor: "pointer",
                  boxShadow: "0 4px 14px rgba(15, 23, 42, 0.2)",
                }}
              >
                Send Bank Verification OTP →
              </button>
            </div>
          )}

          {/* ── STEP 2: Enter OTP ── */}
          {step === 2 && (
            <div>
              <div style={{ textAlign: "center", marginBottom: "24px" }}>
                <div style={{ fontSize: "2rem", marginBottom: "8px" }}>📱</div>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 800, color: "#0F172A", marginBottom: "6px" }}>
                  Verify Bank One-Time Password
                </h3>
                <p style={{ color: "#64748B", fontSize: "0.86rem" }}>
                  Enter the 6-digit OTP sent by <strong>{selectedBank.name}</strong> to{" "}
                  <strong>+91 ******{mobile.slice(-4) || "4920"}</strong>
                </p>
              </div>

              {/* 6-Digit OTP Boxes */}
              <div style={{ display: "flex", justifyContent: "center", gap: "10px", marginBottom: "20px" }}>
                {otpDigits.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => (otpInputRefs.current[idx] = el)}
                    type="text"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(idx, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                    style={{
                      width: "48px",
                      height: "56px",
                      fontSize: "1.5rem",
                      fontWeight: 800,
                      textAlign: "center",
                      borderRadius: "10px",
                      border: "1.5px solid #CBD5E1",
                      background: "#F8FAFC",
                      color: "#0F172A",
                      outline: "none",
                    }}
                  />
                ))}
              </div>

              {/* Sandbox Tip Card */}
              <div
                style={{
                  background: "#EFF6FF",
                  border: "1px solid #BFDBFE",
                  borderRadius: "10px",
                  padding: "10px 14px",
                  fontSize: "0.8rem",
                  color: "#1E40AF",
                  textAlign: "center",
                  marginBottom: "24px",
                }}
              >
                💡 <strong>Verification Tip:</strong> Enter any 6-digit code or leave <code>123456</code> to verify bank credentials.
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", fontSize: "0.84rem" }}>
                <span style={{ color: "#64748B" }}>
                  {timer > 0 ? `Resend OTP in 00:${timer < 10 ? `0${timer}` : timer}` : "Didn't receive code?"}
                </span>
                {timer === 0 && (
                  <button
                    type="button"
                    onClick={() => setTimer(28)}
                    style={{ background: "none", border: "none", color: "#2563EB", fontWeight: 700, cursor: "pointer" }}
                  >
                    Resend OTP
                  </button>
                )}
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  style={{
                    flex: 1,
                    background: "#F1F5F9",
                    border: "1px solid #E2E8F0",
                    color: "#334155",
                    padding: "12px",
                    borderRadius: "10px",
                    fontWeight: 600,
                    fontSize: "0.88rem",
                    cursor: "pointer",
                  }}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  onClick={handleVerifyOtpAndProceed}
                  disabled={loading}
                  style={{
                    flex: 2,
                    background: "#2563EB",
                    color: "#FFFFFF",
                    border: "none",
                    padding: "12px",
                    borderRadius: "10px",
                    fontWeight: 700,
                    fontSize: "0.92rem",
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(37, 99, 235, 0.25)",
                  }}
                >
                  {loading ? "Verifying..." : "Verify OTP & Discover →"}
                </button>
              </div>
            </div>
          )}

          {/* ── STEP 3: Discovered Accounts ── */}
          {step === 3 && (
            <div>
              <div style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                  <span style={{ fontSize: "1.2rem" }}>{selectedBank.icon}</span>
                  <h3 style={{ fontSize: "1.15rem", fontWeight: 800, color: "#0F172A" }}>
                    Accounts Discovered at {selectedBank.name}
                  </h3>
                </div>
                <p style={{ color: "#64748B", fontSize: "0.84rem" }}>
                  Select the accounts you authorize Syntropy to track for expense categorization:
                </p>
              </div>

              {/* Accounts Checkbox List */}
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
                <div
                  style={{
                    padding: "14px 16px",
                    borderRadius: "12px",
                    background: "#FFFFFF",
                    border: "1.5px solid #10B981",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <input type="checkbox" defaultChecked style={{ width: "18px", height: "18px", accentColor: "#059669" }} />
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "0.92rem", color: "#0F172A" }}>
                        Savings Account •••• {mobile.slice(-4) || "4920"}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#64748B" }}>Primary Salary Account • Verified FIP</div>
                    </div>
                  </div>
                  <div style={{ textAlign: "right", fontWeight: 800, color: "#059669", fontSize: "1rem" }}>
                    ₹3,42,850
                  </div>
                </div>

                <div
                  style={{
                    padding: "14px 16px",
                    borderRadius: "12px",
                    background: "#FFFFFF",
                    border: "1.5px solid #10B981",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <input type="checkbox" defaultChecked style={{ width: "18px", height: "18px", accentColor: "#059669" }} />
                    <div>
                      <div style={{ fontWeight: 700, fontSize: "0.92rem", color: "#0F172A" }}>
                        Linked Fixed Deposit •••• 2291
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#64748B" }}>7.1% p.a. Cumulative Reserve</div>
                    </div>
                  </div>
                  <div style={{ textAlign: "right", fontWeight: 800, color: "#0F172A", fontSize: "1rem" }}>
                    ₹88,200
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleFinalizeConsent}
                disabled={loading}
                style={{
                  width: "100%",
                  background: "#059669",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "14px",
                  borderRadius: "12px",
                  fontWeight: 700,
                  fontSize: "0.95rem",
                  cursor: "pointer",
                  boxShadow: "0 4px 14px rgba(5, 150, 105, 0.3)",
                }}
              >
                {loading ? "Connecting..." : "Authorize Consent & Sync Transactions ⚡"}
              </button>
            </div>
          )}

          {/* ── STEP 4: Real-time Ingestion & Decryption ── */}
          {step === 4 && (
            <div style={{ textAlign: "center", padding: "12px 0" }}>
              <div style={{ width: "50px", height: "50px", borderRadius: "50%", border: "3px solid #E2E4E9", borderTopColor: "#059669", animation: "spin 0.8s linear infinite", margin: "0 auto 20px" }} />
              <h3 style={{ fontSize: "1.25rem", fontWeight: 800, color: "#0F172A", marginBottom: "8px" }}>
                Decrypting Financial Information (FI)
              </h3>
              <p style={{ color: "#64748B", fontSize: "0.88rem", marginBottom: "28px" }}>
                Ingesting verified bank transactions from {selectedBank.name}...
              </p>

              {/* Progress Checklist */}
              <div style={{ textAlign: "left", display: "flex", flexDirection: "column", gap: "14px", maxWidth: "420px", margin: "0 auto" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem", color: syncPhase >= 1 ? "#059669" : "#94A3B8", fontWeight: 600 }}>
                  <span>{syncPhase >= 1 ? "✓" : "○"}</span>
                  <span>256-bit encrypted handshake with {selectedBank.fip}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem", color: syncPhase >= 2 ? "#059669" : "#94A3B8", fontWeight: 600 }}>
                  <span>{syncPhase >= 2 ? "✓" : "○"}</span>
                  <span>Ingesting and decrypting 180+ bank statement records</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem", color: syncPhase >= 3 ? "#059669" : "#94A3B8", fontWeight: 600 }}>
                  <span>{syncPhase >= 3 ? "✓" : "○"}</span>
                  <span>AI transaction categorization (Swiggy, Amazon, SIPs)</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem", color: syncPhase >= 4 ? "#059669" : "#94A3B8", fontWeight: 600 }}>
                  <span>{syncPhase >= 4 ? "✓" : "○"}</span>
                  <span>Activating real-time financial health score &amp; dashboard</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
