export function SignalGrid() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.03] dark:opacity-[0.06]" aria-hidden>
      <svg width="100%" height="100%">
        <defs>
          <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M 32 0 L 0 0 0 32" fill="none" stroke="currentColor" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-nova/5 to-transparent animate-[scan_8s_linear_infinite]" />
      <style>{`
        @keyframes scan {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
      `}</style>
    </div>
  );
}
