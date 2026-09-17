import { useEffect, useState } from "react";

export function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const stored = localStorage.getItem("novaa_theme");
    if (stored === "dark" || stored === "light") return stored;
    return "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("novaa_theme", theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === "light" ? "dark" : "light"));
  return { theme, toggle, setTheme };
}
