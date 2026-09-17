import { animate, useMotionValue, useTransform, motion, useReducedMotion } from "motion/react";
import { useEffect } from "react";

type CountUpProps = {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  className?: string;
};

export function CountUp({ value, prefix = "", suffix = "", decimals = 0, className }: CountUpProps) {
  const motionVal = useMotionValue(0);
  const rounded = useTransform(motionVal, (v) =>
    `${prefix}${v.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`,
  );
  const reduce = useReducedMotion();

  useEffect(() => {
    if (reduce) {
      motionVal.set(value);
      return;
    }
    const controls = animate(motionVal, value, { duration: 0.9, ease: [0.22, 1, 0.36, 1] });
    return controls.stop;
  }, [value, motionVal, reduce]);

  return <motion.span className={className}>{rounded}</motion.span>;
}
