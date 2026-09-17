import { cn } from "../../lib/cn";

type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-ink outline-none transition focus:border-nova/50 focus:ring-2 focus:ring-nova/20",
        className,
      )}
      {...props}
    />
  );
}
