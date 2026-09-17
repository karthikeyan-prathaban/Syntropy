import { cn } from "../../lib/cn";

const colors = {
  nova: "bg-nova/10 text-nova",
  jade: "bg-jade/10 text-jade",
  coral: "bg-coral/10 text-coral",
  amber: "bg-amber/10 text-amber",
  muted: "bg-sunken text-muted",
};

export function Badge({
  children,
  color = "muted",
  className,
}: {
  children: React.ReactNode;
  color?: keyof typeof colors;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", colors[color], className)}>
      {children}
    </span>
  );
}
