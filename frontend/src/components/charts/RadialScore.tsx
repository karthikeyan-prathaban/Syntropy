import { motion, useReducedMotion } from "motion/react";
import { CountUp } from "../../motion/CountUp";

export function RadialScore({ score, label = "Health" }: { score: number; label?: string }) {
  const reduce = useReducedMotion();
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r="54" fill="none" stroke="var(--color-sunken)" strokeWidth="10" />
        <motion.circle
          cx="70"
          cy="70"
          r="54"
          fill="none"
          stroke="#5b5bd6"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={reduce ? { duration: 0 } : { duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="absolute text-center">
        <CountUp value={score} className="text-3xl font-bold font-mono text-ink" />
        <div className="text-xs text-muted mt-0.5">{label}</div>
      </div>
    </div>
  );
}
