import { Command } from "cmdk";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";

const routes = [
  { label: "Overview", path: "/app/overview" },
  { label: "Cashflow", path: "/app/cashflow" },
  { label: "Spending", path: "/app/spending" },
  { label: "Accounts", path: "/app/accounts" },
  { label: "Transactions", path: "/app/transactions" },
  { label: "Recall", path: "/app/recall" },
  { label: "AI Insights", path: "/app/insights" },
  { label: "Settings", path: "/app/settings" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", down);
    return () => window.removeEventListener("keydown", down);
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-ink/20 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setOpen(false)}
        >
          <motion.div
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg glass rounded-2xl overflow-hidden shadow-glow"
          >
            <Command className="p-2">
              <Command.Input
                placeholder="Search pages..."
                className="w-full h-12 px-4 text-sm bg-transparent outline-none border-b border-border"
              />
              <Command.List className="max-h-72 overflow-auto p-2">
                <Command.Empty className="py-6 text-center text-sm text-muted">No results.</Command.Empty>
                {routes.map((r) => (
                  <Command.Item
                    key={r.path}
                    onSelect={() => {
                      navigate(r.path);
                      setOpen(false);
                    }}
                    className="flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm cursor-pointer aria-selected:bg-nova/10 aria-selected:text-nova"
                  >
                    {r.label}
                  </Command.Item>
                ))}
              </Command.List>
            </Command>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
