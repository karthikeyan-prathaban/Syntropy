import { motion } from "motion/react";

type LogoProps = {
  size?: number;
  showText?: boolean;
  className?: string;
};

export function Logo({ size = 28, showText = true, className = "" }: LogoProps) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <motion.svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        whileHover={{ rotate: 15, scale: 1.05 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
      >
        <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="1.5" className="text-nova/40" />
        <path
          d="M16 4 L18.5 13.5 L28 16 L18.5 18.5 L16 28 L13.5 18.5 L4 16 L13.5 13.5 Z"
          className="fill-nova"
        />
        <circle cx="16" cy="16" r="2.5" className="fill-aurora" />
      </motion.svg>
      {showText && (
        <span className="text-lg font-bold tracking-tight text-ink">
          NOV<span className="text-nova">AA</span>
        </span>
      )}
    </div>
  );
}
