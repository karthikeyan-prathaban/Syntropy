import { Slot } from "@radix-ui/react-slot";
import { cn } from "../../lib/cn";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  asChild?: boolean;
};

const variants = {
  primary: "bg-nova text-white hover:bg-nova/90 shadow-glow",
  secondary: "bg-sunken text-ink hover:bg-sunken/80",
  ghost: "hover:bg-sunken text-ink",
  outline: "border border-border bg-surface hover:bg-sunken",
};

const sizes = {
  sm: "h-8 px-3 text-sm rounded-lg",
  md: "h-10 px-4 text-sm rounded-xl",
  lg: "h-12 px-6 text-base rounded-xl",
};

export function Button({
  className,
  variant = "primary",
  size = "md",
  asChild,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center font-medium transition-all disabled:opacity-50 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
