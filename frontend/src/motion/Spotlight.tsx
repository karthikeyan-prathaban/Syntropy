import { useRef } from "react";

type SpotlightProps = {
  children: React.ReactNode;
  className?: string;
};

export function Spotlight({ children, className = "" }: SpotlightProps) {
  const ref = useRef<HTMLDivElement>(null);

  const onMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--mouse-x", `${e.clientX - rect.left}px`);
    el.style.setProperty("--mouse-y", `${e.clientY - rect.top}px`);
  };

  return (
    <div ref={ref} className={`spotlight-card ${className}`} onMouseMove={onMove}>
      {children}
    </div>
  );
}
