import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  PieChart,
  Wallet,
  List,
  Search,
  Sparkles,
  Settings,
  Moon,
  Sun,
  LogOut,
} from "lucide-react";
import { Logo } from "../components/brand/Logo";
import { AuroraBackdrop } from "../components/brand/AuroraBackdrop";
import { SignalGrid } from "../components/brand/SignalGrid";
import { CommandPalette } from "./CommandPalette";
import { useTheme } from "./ThemeProvider";
import { cn } from "../lib/cn";

const nav = [
  { to: "/app/overview", icon: LayoutDashboard, label: "Overview" },
  { to: "/app/cashflow", icon: TrendingUp, label: "Cashflow" },
  { to: "/app/spending", icon: PieChart, label: "Spending" },
  { to: "/app/accounts", icon: Wallet, label: "Accounts" },
  { to: "/app/transactions", icon: List, label: "Transactions" },
  { to: "/app/recall", icon: Search, label: "Recall" },
  { to: "/app/insights", icon: Sparkles, label: "Insights" },
  { to: "/app/settings", icon: Settings, label: "Settings" },
];

export function AppShell() {
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const logout = () => {
    localStorage.removeItem("novaa_token");
    localStorage.removeItem("novaa_user");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <AuroraBackdrop />
      <SignalGrid />
      <CommandPalette />
      <div className="flex min-h-screen">
        <aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col border-r border-border bg-surface/80 backdrop-blur-xl">
          <div className="p-5 border-b border-border">
            <Logo />
            <p className="text-[10px] text-muted mt-1 tracking-wide">ANALYTICS WORKSPACE</p>
          </div>
          <nav className="flex-1 p-3 space-y-0.5">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive ? "bg-nova/10 text-nova" : "text-muted hover:bg-sunken hover:text-ink",
                  )
                }
              >
                <item.icon size={18} />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="p-3 border-t border-border space-y-1">
            <button
              onClick={toggle}
              className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm text-muted hover:bg-sunken hover:text-ink"
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
              {theme === "light" ? "Dark mode" : "Light mode"}
            </button>
            <button
              onClick={logout}
              className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm text-muted hover:bg-coral/10 hover:text-coral"
            >
              <LogOut size={18} />
              Sign out
            </button>
          </div>
        </aside>
        <main className="ml-60 flex-1 p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
