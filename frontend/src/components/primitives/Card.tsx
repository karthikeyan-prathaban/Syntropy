import { cn } from "../../lib/cn";
import { Spotlight } from "../../motion/Spotlight";

type CardProps = {
  children: React.ReactNode;
  className?: string;
  spotlight?: boolean;
};

export function Card({ children, className, spotlight = false }: CardProps) {
  const inner = (
    <div className={cn("glass rounded-2xl p-5", className)}>{children}</div>
  );
  return spotlight ? <Spotlight className="rounded-2xl">{inner}</Spotlight> : inner;
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h3 className={cn("text-sm font-semibold text-muted uppercase tracking-wide", className)}>{children}</h3>;
}

export function CardValue({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("text-2xl font-bold font-mono text-ink mt-1", className)}>{children}</div>;
}
