import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { consentApi } from "../lib/api";
import { Logo } from "../components/brand/Logo";
import { Card } from "../components/primitives/Card";
import { motion } from "motion/react";

const STEPS = ["Consent received", "Verifying with AA", "Fetching accounts", "Parsing transactions", "Ready"];

export function ConsentCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const requestId = params.get("id") || params.get("requestId") || localStorage.getItem("novaa_consent_request");
    if (!requestId) {
      setError("No consent ID found");
      return;
    }

    let attempts = 0;
    const poll = async () => {
      try {
        setStep(1);
        const statusRes = await consentApi.status(requestId);
        if (["ACTIVE", "APPROVED", "SUCCESS"].includes(statusRes.data.status)) {
          setStep(2);
          setStep(3);
          await consentApi.fetch(requestId);
          setStep(4);
          setTimeout(() => navigate("/app/overview"), 1200);
          return;
        }
        attempts++;
        if (attempts < 15) setTimeout(poll, 3000);
        else setError("Consent not approved in time");
      } catch {
        setError("Failed to process consent");
      }
    };
    setStep(0);
    poll();
  }, [params, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas">
      <Card className="w-full max-w-md text-center">
        <Logo className="justify-center mb-6" />
        <h1 className="text-lg font-semibold">Connecting your bank</h1>
        <p className="text-sm text-muted mt-1">Secure Account Aggregator pipeline</p>

        <div className="mt-8 space-y-3">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-3 text-sm">
              <motion.div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                  i <= step ? "bg-jade text-white" : "bg-sunken text-muted"
                }`}
                initial={{ scale: 0.8 }}
                animate={{ scale: i === step ? 1.1 : 1 }}
              >
                {i < step ? "✓" : i + 1}
              </motion.div>
              <span className={i <= step ? "text-ink" : "text-muted"}>{label}</span>
            </div>
          ))}
        </div>

        {error && (
          <p className="text-coral text-sm mt-6">{error}</p>
        )}
      </Card>
    </div>
  );
}
