import { motion, useReducedMotion } from "motion/react";
import { useRef } from "react";
import { springs } from "./tokens";

type MagneticProps = {
  children: React.ReactNode;
  className?: string;
};

export function Magnetic({ children, className }: MagneticProps) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  const handleMove = (e: React.MouseEvent) => {
    if (reduce || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    const dist = Math.hypot(x, y);
    if (dist < 80) {
      ref.current.style.transform = `translate(${x * 0.15}px, ${y * 0.15}px)`;
    }
  };

  const handleLeave = () => {
    if (ref.current) ref.current.style.transform = "";
  };

  return (
    <motion.div
      ref={ref}
      className={className}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      transition={springs.snap}
    >
      {children}
    </motion.div>
  );
}
