import { useEffect, useState } from "react";

export function AuroraBackdrop() {
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const onVis = () => setPaused(document.hidden);
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <div
        className={`absolute -top-1/4 left-1/4 h-[500px] w-[500px] rounded-full bg-nova/10 blur-[120px] dark:bg-nova/25 ${paused ? "" : "animate-[drift_28s_ease-in-out_infinite]"}`}
      />
      <div
        className={`absolute top-1/3 right-1/4 h-[400px] w-[400px] rounded-full bg-aurora/10 blur-[100px] dark:bg-aurora/20 ${paused ? "" : "animate-[drift_32s_ease-in-out_infinite_reverse]"}`}
      />
      <div
        className={`absolute bottom-0 left-1/2 h-[350px] w-[350px] rounded-full bg-jade/8 blur-[90px] dark:bg-jade/15 ${paused ? "" : "animate-[drift_24s_ease-in-out_infinite]"}`}
      />
      <style>{`
        @keyframes drift {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -20px) scale(1.05); }
          66% { transform: translate(-20px, 15px) scale(0.95); }
        }
      `}</style>
    </div>
  );
}
